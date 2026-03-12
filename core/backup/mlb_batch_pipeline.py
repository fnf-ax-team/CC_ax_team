"""
MLB Batch Pipeline for Production Image Generation

Handles batch processing of multiple outfits across multiple shot presets
with parallel execution, auto-retry, and progress tracking.

Author: FNF Studio
Version: 1.0.0
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from PIL import Image

from core.mlb_a2z_generator import MLBBrandcutGenerator, GenerationResult
from core.brandcut import MLBValidator, MLBQualityTier as QualityTier
from core.diversity_engine import DiversityEngine, DiversityCombination


@dataclass
class BatchConfig:
    """Configuration for batch processing"""

    max_workers: int = 4
    max_retries: int = 2
    retry_delay: float = 5.0
    save_intermediate: bool = True
    stop_on_critical_failure: bool = False
    use_diversity_engine: bool = True  # Enable diversity enforcement
    style_library_path: str = None  # Path to MLB style library


@dataclass
class OutfitSet:
    """Represents one outfit to process"""

    outfit_id: str
    outfit_folder: str
    face_folder: str
    presets: Optional[List[str]] = None  # None = all presets


@dataclass
class BatchResult:
    """Result of batch processing"""

    total_generated: int
    release_ready: int
    needs_work: int
    failed: int
    results: List[Dict]
    report_path: str
    duration_seconds: float


class MLBBatchPipeline:
    """
    Production batch pipeline for MLB brandcut generation.

    Features:
    - Parallel processing with configurable workers
    - Auto-retry on failure
    - Progress tracking with callbacks
    - Quality tier classification
    - Comprehensive reporting

    Example:
        ```python
        generator = MLBBrandcutGenerator(api_key="key1,key2,key3")
        validator = MLBValidator(client=generator._client)
        pipeline = MLBBatchPipeline(generator, validator)

        outfits = [
            OutfitSet(
                outfit_id="outfit_01",
                outfit_folder="./outfits/01",
                face_folder="./faces/model_a",
                presets=["urban_street_confident", "industrial_lean"]
            )
        ]

        result = pipeline.run_batch(
            outfit_sets=outfits,
            output_dir="./output",
            presets=None  # Use OutfitSet.presets
        )
        ```
    """

    def __init__(
        self,
        generator: MLBBrandcutGenerator,
        validator: MLBValidator,
        config: Optional[BatchConfig] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """
        Initialize the batch pipeline.

        Args:
            generator: MLBBrandcutGenerator instance
            validator: MLBValidator instance
            config: BatchConfig for processing options
            progress_callback: Called with (current, total, message)
        """
        self.generator = generator
        self.validator = validator
        self.config = config or BatchConfig()
        self.progress_callback = progress_callback
        self.logger = logging.getLogger(__name__)

        # Configure logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize diversity engine if enabled
        self.diversity_engine = None
        if self.config.use_diversity_engine:
            style_lib_path = (
                self.config.style_library_path
                or ".claude/skills/brand-dna/mlb-style-library.json"
            )
            self.diversity_engine = DiversityEngine(style_lib_path)
            self.logger.info(f"DiversityEngine initialized with {style_lib_path}")

    def run_batch(
        self,
        outfit_sets: List[OutfitSet],
        output_dir: str,
        presets: Optional[List[str]] = None,
    ) -> BatchResult:
        """
        Run batch generation for multiple outfits.

        Args:
            outfit_sets: List of OutfitSet to process
            output_dir: Base output directory
            presets: Global presets to use (overrides OutfitSet.presets if provided)

        Returns:
            BatchResult with all processing results
        """
        self.logger.info(f"Starting batch processing: {len(outfit_sets)} outfit(s)")
        start_time = datetime.now()
        os.makedirs(output_dir, exist_ok=True)

        # Prepare tasks
        tasks = self._prepare_tasks(outfit_sets, presets)
        self.logger.info(f"Total tasks: {len(tasks)}")

        results = []

        # Execute with parallel workers
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._process_single, task, output_dir): task
                for task in tasks
            }

            for i, future in enumerate(as_completed(futures)):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Progress callback
                    if self.progress_callback:
                        status = (
                            "SUCCESS"
                            if result.get("tier") == "RELEASE_READY"
                            else "DONE"
                        )
                        self.progress_callback(
                            i + 1,
                            len(tasks),
                            f"{task['outfit_id']}/{task['preset_id']}: {status}",
                        )

                    self.logger.info(
                        f"[{i+1}/{len(tasks)}] {task['outfit_id']}/{task['preset_id']}: "
                        f"Tier={result.get('tier', 'UNKNOWN')}"
                    )

                except Exception as e:
                    self.logger.error(f"Task failed: {e}", exc_info=True)
                    results.append(
                        {
                            "outfit_id": task["outfit_id"],
                            "preset_id": task["preset_id"],
                            "success": False,
                            "error": str(e),
                            "tier": "FAILED",
                        }
                    )

                    if self.config.stop_on_critical_failure:
                        self.logger.error("Stopping due to critical failure")
                        break

        # Generate report
        duration = (datetime.now() - start_time).total_seconds()
        report_path = self._generate_report(results, output_dir, duration)

        # Calculate stats
        release_ready = sum(1 for r in results if r.get("tier") == "RELEASE_READY")
        needs_work = sum(
            1 for r in results if r.get("tier") in ["NEEDS_MINOR_EDIT", "NEEDS_WORK"]
        )
        failed = sum(1 for r in results if not r.get("success", True))
        total_generated = len([r for r in results if r.get("success", True)])

        self.logger.info(
            f"Batch complete: {total_generated} generated, "
            f"{release_ready} release-ready, {needs_work} needs work, "
            f"{failed} failed"
        )

        return BatchResult(
            total_generated=total_generated,
            release_ready=release_ready,
            needs_work=needs_work,
            failed=failed,
            results=results,
            report_path=report_path,
            duration_seconds=duration,
        )

    def _prepare_tasks(
        self, outfit_sets: List[OutfitSet], presets: Optional[List[str]]
    ) -> List[Dict]:
        """
        Prepare list of generation tasks.

        Args:
            outfit_sets: List of OutfitSet to process
            presets: Global presets (overrides OutfitSet.presets if provided)

        Returns:
            List of task dictionaries with outfit and preset information
        """
        all_presets = presets or self.generator.get_preset_ids()
        tasks = []

        for outfit in outfit_sets:
            # Use global presets if provided, else use outfit-specific presets
            outfit_presets = presets or outfit.presets or all_presets

            for preset_id in outfit_presets:
                tasks.append(
                    {
                        "outfit_id": outfit.outfit_id,
                        "outfit_folder": outfit.outfit_folder,
                        "face_folder": outfit.face_folder,
                        "preset_id": preset_id,
                    }
                )

        # Apply diversity combinations if enabled
        if self.diversity_engine:
            for i, task in enumerate(tasks):
                combo = self.diversity_engine.select_combination(i, len(tasks))
                task["diversity_combo"] = combo
                self.logger.debug(
                    f"Task {i+1}/{len(tasks)}: Applied diversity combo "
                    f"(background={combo.background_id}, clothing={combo.clothing_id}, "
                    f"lighting={combo.lighting_id})"
                )

        return tasks

    def _process_single(self, task: Dict, output_dir: str) -> Dict:
        """
        Process a single generation task with retry logic.

        Args:
            task: Task dictionary with outfit and preset information
            output_dir: Base output directory

        Returns:
            Result dictionary with generation outcome and quality tier
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                # Apply diversity combination if available
                diversity_additions = ""
                if "diversity_combo" in task and self.diversity_engine:
                    combo = task["diversity_combo"]
                    diversity_additions = self.diversity_engine.build_prompt_additions(
                        combo
                    )
                    self.logger.debug(
                        f"Applying diversity to {task['outfit_id']}/{task['preset_id']}: {diversity_additions[:100]}..."
                    )

                # Generate image
                result = self.generator.generate_single(
                    preset_id=task["preset_id"],
                    face_folder=task["face_folder"],
                    outfit_folder=task["outfit_folder"],
                    validate=False,  # We'll validate manually for tier classification
                    custom_prompt_additions=diversity_additions,  # Pass diversity additions
                )

                if result.image and result.success:
                    # Perform validation with tier classification
                    preset = self.generator.get_preset_by_id(task["preset_id"])

                    face_images = self.generator._get_images_from_folder(
                        task["face_folder"], max_images=5
                    )
                    outfit_images = self.generator._get_images_from_folder(
                        task["outfit_folder"], max_images=5
                    )

                    validation_result = self.validator.validate(
                        generated_img=result.image,
                        face_images=face_images,
                        outfit_images=outfit_images,
                        shot_preset={
                            "shot_id": preset.get("id", "unknown"),
                            "pose": preset.get("pose", "N/A"),
                            "expression": preset.get("expression", "N/A"),
                            "framing": preset.get("framing", "N/A"),
                            "background": preset.get("background", "N/A"),
                        },
                    )

                    tier = validation_result.tier.value

                    # Save to appropriate folder
                    sub_folder = "release" if tier == "RELEASE_READY" else "review"
                    save_dir = os.path.join(output_dir, task["outfit_id"], sub_folder)
                    os.makedirs(save_dir, exist_ok=True)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{task['preset_id']}_{timestamp}.png"
                    filepath = os.path.join(save_dir, filename)
                    result.image.save(filepath)

                    # Save validation report alongside image
                    if self.config.save_intermediate:
                        validation_path = filepath.replace(".png", "_validation.json")
                        with open(validation_path, "w", encoding="utf-8") as f:
                            json.dump(
                                validation_result.to_dict(),
                                f,
                                ensure_ascii=False,
                                indent=2,
                            )

                    return {
                        "outfit_id": task["outfit_id"],
                        "preset_id": task["preset_id"],
                        "success": True,
                        "filepath": filepath,
                        "tier": tier,
                        "validation": validation_result.to_dict(),
                        "attempt": attempt + 1,
                        "total_score": validation_result.total_score,
                        "issues": validation_result.issues,
                        "strengths": validation_result.strengths,
                    }

                # No image generated
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"No image generated for {task['outfit_id']}/{task['preset_id']}, "
                        f"retrying (attempt {attempt + 2}/{self.config.max_retries + 1})"
                    )
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue

            except Exception as e:
                error_msg = str(e)
                self.logger.error(
                    f"Error generating {task['outfit_id']}/{task['preset_id']}: {error_msg}"
                )

                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"Retrying after {self.config.retry_delay * (attempt + 1)}s "
                        f"(attempt {attempt + 2}/{self.config.max_retries + 1})"
                    )
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    return {
                        "outfit_id": task["outfit_id"],
                        "preset_id": task["preset_id"],
                        "success": False,
                        "error": error_msg,
                        "attempts": attempt + 1,
                        "tier": "FAILED",
                    }

        return {
            "outfit_id": task["outfit_id"],
            "preset_id": task["preset_id"],
            "success": False,
            "error": "Max retries exceeded",
            "tier": "FAILED",
        }

    def _generate_report(
        self, results: List[Dict], output_dir: str, duration: float
    ) -> str:
        """
        Generate comprehensive batch processing report.

        Args:
            results: List of result dictionaries
            output_dir: Output directory
            duration: Total processing time in seconds

        Returns:
            Path to saved report file
        """
        # Calculate statistics
        total_tasks = len(results)
        successful = sum(1 for r in results if r.get("success", False))
        failed = total_tasks - successful

        tier_counts = {
            "RELEASE_READY": 0,
            "NEEDS_MINOR_EDIT": 0,
            "NEEDS_WORK": 0,
            "REGENERATE": 0,
            "FAILED": 0,
        }

        for r in results:
            tier = r.get("tier", "FAILED")
            if tier in tier_counts:
                tier_counts[tier] += 1
            elif tier in ["NEEDS_MINOR_EDIT", "NEEDS_WORK"]:
                tier_counts["NEEDS_WORK"] = tier_counts.get("NEEDS_WORK", 0) + 1

        # Calculate average scores for successful validations
        valid_scores = [
            r.get("total_score", 0)
            for r in results
            if r.get("success", False) and r.get("total_score")
        ]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

        # Group by outfit
        by_outfit = {}
        for r in results:
            outfit_id = r.get("outfit_id", "unknown")
            if outfit_id not in by_outfit:
                by_outfit[outfit_id] = []
            by_outfit[outfit_id].append(r)

        # Build report
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "duration_formatted": f"{int(duration // 60)}m {int(duration % 60)}s",
            "total_tasks": total_tasks,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total_tasks * 100, 1)
            if total_tasks > 0
            else 0,
            "by_tier": {
                "RELEASE_READY": tier_counts["RELEASE_READY"],
                "NEEDS_MINOR_EDIT": tier_counts.get("NEEDS_MINOR_EDIT", 0),
                "NEEDS_WORK": tier_counts.get("NEEDS_WORK", 0),
                "REGENERATE": tier_counts.get("REGENERATE", 0),
                "FAILED": tier_counts["FAILED"],
            },
            "release_ready_rate": round(
                tier_counts["RELEASE_READY"] / successful * 100, 1
            )
            if successful > 0
            else 0,
            "usable_rate": round(
                (tier_counts["RELEASE_READY"] + tier_counts.get("NEEDS_MINOR_EDIT", 0))
                / successful
                * 100,
                1,
            )
            if successful > 0
            else 0,
            "average_score": round(avg_score, 1),
            "by_outfit": {},
            "results": results,
        }

        # Add per-outfit breakdown
        for outfit_id, outfit_results in by_outfit.items():
            outfit_stats = {
                "total": len(outfit_results),
                "successful": sum(1 for r in outfit_results if r.get("success", False)),
                "release_ready": sum(
                    1 for r in outfit_results if r.get("tier") == "RELEASE_READY"
                ),
                "needs_work": sum(
                    1
                    for r in outfit_results
                    if r.get("tier") in ["NEEDS_MINOR_EDIT", "NEEDS_WORK"]
                ),
                "failed": sum(1 for r in outfit_results if not r.get("success", False)),
                "presets": [r.get("preset_id", "unknown") for r in outfit_results],
            }
            report["by_outfit"][outfit_id] = outfit_stats

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"batch_report_{timestamp}.json")

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Report saved: {report_path}")

        # Also create a human-readable summary
        summary_path = os.path.join(output_dir, f"batch_summary_{timestamp}.txt")
        self._write_summary(report, summary_path)

        return report_path

    def _write_summary(self, report: dict, summary_path: str) -> None:
        """Write human-readable summary text file"""
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("MLB BATCH GENERATION REPORT\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Timestamp: {report['timestamp']}\n")
            f.write(f"Duration: {report['duration_formatted']}\n\n")

            f.write("OVERALL STATISTICS:\n")
            f.write(f"  Total Tasks: {report['total_tasks']}\n")
            f.write(
                f"  Successful: {report['successful']} ({report['success_rate']}%)\n"
            )
            f.write(f"  Failed: {report['failed']}\n\n")

            f.write("QUALITY TIER BREAKDOWN:\n")
            tiers = report["by_tier"]
            f.write(
                f"  ✅ Release Ready: {tiers['RELEASE_READY']} ({report['release_ready_rate']}%)\n"
            )
            f.write(f"  ⚠️  Needs Minor Edit: {tiers['NEEDS_MINOR_EDIT']}\n")
            f.write(f"  🔄 Needs Work: {tiers['NEEDS_WORK']}\n")
            f.write(f"  ❌ Regenerate: {tiers['REGENERATE']}\n")
            f.write(f"  💥 Failed: {tiers['FAILED']}\n")
            f.write(f"  📈 Usable Rate: {report['usable_rate']}%\n\n")

            if report["average_score"] > 0:
                f.write(f"Average Quality Score: {report['average_score']}/100\n\n")

            f.write("PER-OUTFIT BREAKDOWN:\n")
            for outfit_id, stats in report["by_outfit"].items():
                f.write(f"\n  {outfit_id}:\n")
                f.write(f"    Total: {stats['total']}\n")
                f.write(f"    Release Ready: {stats['release_ready']}\n")
                f.write(f"    Needs Work: {stats['needs_work']}\n")
                f.write(f"    Failed: {stats['failed']}\n")
                f.write(f"    Presets: {', '.join(stats['presets'])}\n")

            f.write("\n" + "=" * 70 + "\n")

    def retry_failed(self, report_path: str, output_dir: str) -> BatchResult:
        """
        Retry failed tasks from previous batch.

        Args:
            report_path: Path to previous batch report JSON
            output_dir: Output directory for retry results

        Returns:
            BatchResult with retry outcomes
        """
        self.logger.info(f"Loading previous report: {report_path}")

        with open(report_path, "r", encoding="utf-8") as f:
            previous_report = json.load(f)

        # Extract failed and regenerate tasks
        tasks_to_retry = []
        for result in previous_report.get("results", []):
            tier = result.get("tier", "FAILED")
            if tier in ["FAILED", "REGENERATE"] or not result.get("success", False):
                tasks_to_retry.append(
                    {
                        "outfit_id": result.get("outfit_id", "unknown"),
                        "preset_id": result.get("preset_id", "unknown"),
                        "outfit_folder": result.get("outfit_folder", ""),
                        "face_folder": result.get("face_folder", ""),
                    }
                )

        if not tasks_to_retry:
            self.logger.info("No tasks to retry")
            return BatchResult(
                total_generated=0,
                release_ready=0,
                needs_work=0,
                failed=0,
                results=[],
                report_path="",
                duration_seconds=0,
            )

        self.logger.info(f"Retrying {len(tasks_to_retry)} task(s)")

        # Process retry tasks
        start_time = datetime.now()
        results = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._process_single, task, output_dir): task
                for task in tasks_to_retry
            }

            for i, future in enumerate(as_completed(futures)):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    self.logger.info(
                        f"[{i+1}/{len(tasks_to_retry)}] {task['outfit_id']}/{task['preset_id']}: "
                        f"Tier={result.get('tier', 'UNKNOWN')}"
                    )

                except Exception as e:
                    self.logger.error(f"Retry failed: {e}", exc_info=True)
                    results.append(
                        {
                            "outfit_id": task["outfit_id"],
                            "preset_id": task["preset_id"],
                            "success": False,
                            "error": str(e),
                            "tier": "FAILED",
                        }
                    )

        # Generate retry report
        duration = (datetime.now() - start_time).total_seconds()
        report_path = self._generate_report(results, output_dir, duration)

        # Calculate stats
        release_ready = sum(1 for r in results if r.get("tier") == "RELEASE_READY")
        needs_work = sum(
            1 for r in results if r.get("tier") in ["NEEDS_MINOR_EDIT", "NEEDS_WORK"]
        )
        failed = sum(1 for r in results if not r.get("success", True))
        total_generated = len([r for r in results if r.get("success", True)])

        return BatchResult(
            total_generated=total_generated,
            release_ready=release_ready,
            needs_work=needs_work,
            failed=failed,
            results=results,
            report_path=report_path,
            duration_seconds=duration,
        )

    def print_summary(self, result: BatchResult) -> None:
        """
        Print batch result summary to console.

        Args:
            result: BatchResult from run_batch or retry_failed
        """
        print("\n" + "=" * 70)
        print("MLB BATCH PROCESSING SUMMARY")
        print("=" * 70)
        print(f"\nTotal Generated: {result.total_generated}")
        print(f"✅ Release Ready: {result.release_ready}")
        print(f"⚠️  Needs Work: {result.needs_work}")
        print(f"❌ Failed: {result.failed}")
        print(f"\n⏱️  Duration: {result.duration_seconds:.1f}s")
        print(f"📊 Report: {result.report_path}")
        print("=" * 70 + "\n")


# Convenience function for simple batch processing
def run_simple_batch(
    api_key: str,
    outfit_folder: str,
    face_folder: str,
    output_dir: str,
    presets: Optional[List[str]] = None,
    max_workers: int = 4,
) -> BatchResult:
    """
    Run a simple batch for a single outfit across all (or specified) presets.

    Args:
        api_key: Gemini API key(s)
        outfit_folder: Path to outfit images
        face_folder: Path to face reference images
        output_dir: Output directory
        presets: Optional list of preset IDs (default: all presets)
        max_workers: Number of parallel workers

    Returns:
        BatchResult with processing outcomes
    """
    from google import genai

    # Initialize components
    generator = MLBBrandcutGenerator(
        api_key=api_key, face_folder=face_folder, output_dir=output_dir
    )

    client = genai.Client(api_key=api_key.split(",")[0])
    validator = MLBValidator(client=client)

    config = BatchConfig(max_workers=max_workers)
    pipeline = MLBBatchPipeline(generator, validator, config)

    # Create outfit set
    outfit_set = OutfitSet(
        outfit_id=Path(outfit_folder).name,
        outfit_folder=outfit_folder,
        face_folder=face_folder,
        presets=presets,
    )

    # Run batch
    result = pipeline.run_batch(
        outfit_sets=[outfit_set], output_dir=output_dir, presets=None
    )

    pipeline.print_summary(result)

    return result
