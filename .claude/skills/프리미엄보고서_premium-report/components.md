# Report Components Reference

Copy-paste-ready HTML/CSS/JS patterns for report components. Adapt colors, fonts, and spacing to match each report's unique aesthetic direction.

---

## 1. Scroll Progress Bar

```css
.scroll-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 2px;
  background: rgba(255, 255, 255, 0.6);
  z-index: 10001;
  width: 0%;
  transition: width 0.1s linear;
}
```

```html
<div class="scroll-progress" id="scrollProgress"></div>
```

```js
window.addEventListener('scroll', function() {
  var scrollTop = window.scrollY;
  var docHeight = document.documentElement.scrollHeight - window.innerHeight;
  var pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
  document.getElementById('scrollProgress').style.width = pct + '%';
}, { passive: true });
```

---

## 2. Fixed Navbar with Section Tracking

```css
.navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 10000;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  background: transparent;
  border-bottom: 1px solid transparent;
}
.navbar.scrolled {
  background: rgba(10, 10, 10, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(34, 34, 34, 0.6);
}
.navbar-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
}
.navbar-nav a.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 1.25rem; right: 1.25rem;
  height: 1px;
  background: var(--text-primary);
}
```

```html
<nav class="navbar" id="navbar">
  <div class="navbar-inner">
    <a class="navbar-logo" href="#">REPORT TITLE</a>
    <ul class="navbar-nav" id="navLinks">
      <li><a href="#section1" data-section="section1">Section 1</a></li>
      <li><a href="#section2" data-section="section2">Section 2</a></li>
    </ul>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">
      <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
    </button>
  </div>
</nav>
```

**Section tracking JS** — highlights active nav link based on scroll position:

```js
var navLinks = document.querySelectorAll('#navLinks a[data-section]');
var sections = [];
navLinks.forEach(function(link) {
  var el = document.getElementById(link.getAttribute('data-section'));
  if (el) sections.push({ id: link.getAttribute('data-section'), el: el, link: link });
});

window.addEventListener('scroll', function() {
  var current = '';
  for (var i = sections.length - 1; i >= 0; i--) {
    if (sections[i].el.getBoundingClientRect().top <= 120) {
      current = sections[i].id;
      break;
    }
  }
  navLinks.forEach(function(link) {
    link.classList.toggle('active', link.getAttribute('data-section') === current);
  });
}, { passive: true });
```

---

## 3. Theme Toggle (Dark/Light)

```css
.theme-toggle {
  background: none;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.3s;
}
.theme-toggle .icon-sun { display: none; }
.theme-toggle .icon-moon { display: block; }
html.theme-light .theme-toggle .icon-sun { display: block; }
html.theme-light .theme-toggle .icon-moon { display: none; }
```

```js
(function(){
  var toggle = document.getElementById('themeToggle');
  var html = document.documentElement;
  var saved = localStorage.getItem('report-theme');
  if (saved === 'light') html.classList.add('theme-light');
  toggle.addEventListener('click', function(){
    html.classList.toggle('theme-light');
    localStorage.setItem('report-theme',
      html.classList.contains('theme-light') ? 'light' : 'dark');
  });
})();
```

---

## 4. Hero Section (100vh)

```css
.hero {
  height: 100vh;
  min-height: 800px;
  position: relative;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to bottom,
    rgba(10,10,10,0.3) 0%, rgba(10,10,10,0.1) 30%, rgba(10,10,10,0.7) 100%);
  z-index: 1;
}
.hero-content {
  position: relative; z-index: 2;
  padding: 0 var(--content-padding) clamp(5rem, 10vh, 10rem);
  max-width: var(--max-width);
  margin: 0 auto; width: 100%;
}
.hero-eyebrow {
  font-size: 0.8rem; font-weight: 500;
  letter-spacing: 0.35em; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 2rem;
}
.hero-title {
  font-weight: 300;
  font-size: clamp(3rem, 7vw, 6rem);
  letter-spacing: -0.02em; line-height: 1.08;
  margin-bottom: 1.5rem;
}
```

```html
<section class="hero">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <p class="hero-eyebrow fade-up">Eyebrow Label</p>
    <h1 class="hero-title fade-up stagger-1">Report <em>Title</em></h1>
    <p class="hero-subtitle fade-up stagger-2">Subtitle text here</p>
    <div class="hero-divider fade-up stagger-3"></div>
    <p class="hero-date fade-up stagger-4">March 2026</p>
  </div>
</section>
```

---

## 5. Table of Contents

```css
.toc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0;
}
.toc-item {
  padding: 2.5rem 2rem;
  cursor: pointer;
  transition: background 0.3s;
  text-decoration: none; color: inherit;
  border-right: 1px solid var(--border-subtle);
}
.toc-item:last-child { border-right: none; }
.toc-item:hover { background: rgba(255,255,255,0.03); }
.toc-num {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: 300; font-style: italic;
  color: rgba(255,255,255,0.22);
  margin-bottom: 1.5rem; line-height: 1;
}
```

```html
<div class="toc-grid">
  <a class="toc-item fade-up" href="#section1">
    <div class="toc-num">01</div>
    <div class="toc-text">
      <h3>Section Title</h3>
      <p>Brief description</p>
    </div>
  </a>
  <!-- Repeat for each section -->
</div>
```

---

## 6. Fade-Up Animations

```css
.fade-up {
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-up.visible {
  opacity: 1;
  transform: translateY(0);
}
.fade-up.stagger-1 { transition-delay: 0.1s; }
.fade-up.stagger-2 { transition-delay: 0.2s; }
.fade-up.stagger-3 { transition-delay: 0.3s; }
.fade-up.stagger-4 { transition-delay: 0.4s; }
.fade-up.stagger-5 { transition-delay: 0.5s; }
```

```js
var observer = new IntersectionObserver(function(entries) {
  entries.forEach(function(entry) {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { root: null, rootMargin: '0px 0px -60px 0px', threshold: 0.1 });

document.querySelectorAll('.fade-up').forEach(function(el) {
  observer.observe(el);
});
```

---

## 7. Section Headers (Eyebrow + Title Pattern)

```css
.section-eyebrow {
  font-size: 0.85rem; font-weight: 600;
  letter-spacing: 0.3em; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 1.25rem;
}
.section-title {
  font-weight: 300;
  font-size: clamp(2.5rem, 5vw, 4rem);
  letter-spacing: -0.02em; line-height: 1.12;
  margin-bottom: 0.75rem;
}
.section-desc {
  font-size: 1.1rem; color: var(--text-secondary);
  max-width: 800px; line-height: 1.85; margin-bottom: 3rem;
}
```

```html
<div class="fade-up">
  <p class="section-eyebrow">01 / Topic Label</p>
  <h2 class="section-title">Section <em>Title</em></h2>
  <p class="section-desc">Description paragraph with context.</p>
</div>
```

---

## 8. Data Table

```css
.data-table {
  width: 100%;
  border-collapse: separate; border-spacing: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 16px; overflow: hidden;
}
.data-table th {
  background: var(--bg-secondary);
  font-weight: 600; font-size: 0.85rem;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-secondary); padding: 1.25rem 2rem;
}
.data-table td {
  background: var(--bg-card);
  padding: 1.25rem 2rem;
  border-bottom: 1px solid var(--border-subtle);
}
.data-table tr:last-child td { border-bottom: none; }
.text-good { color: var(--accent-good); font-weight: 600; }
.text-bad { color: var(--accent-bad); }
```

```html
<table class="data-table fade-up">
  <thead>
    <tr><th>Column A</th><th>Column B</th><th>Status</th></tr>
  </thead>
  <tbody>
    <tr><td>Item 1</td><td>Value</td><td class="text-good">Active</td></tr>
    <tr><td>Item 2</td><td>Value</td><td class="text-bad">Inactive</td></tr>
  </tbody>
</table>
```

---

## 9. Cards

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 2.5rem;
  transition: border-color 0.3s;
}
.card:hover { border-color: var(--border-hover); }
```

---

## 10. KPI / Stat Cards

```css
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 3rem 2rem;
  text-align: center;
  transition: border-color 0.3s;
}
.stat-card:hover { border-color: var(--border-hover); }
.stat-number {
  font-size: clamp(3rem, 6vw, 4.5rem);
  font-weight: 300; letter-spacing: -0.02em;
  margin-bottom: 0.5rem; line-height: 1;
}
.stat-label {
  font-size: 0.75rem; font-weight: 600;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--text-muted);
}
```

```html
<div class="stats-grid fade-up">
  <div class="stat-card">
    <div class="stat-number" style="color: var(--accent-good)">95%</div>
    <div class="stat-label">Accuracy</div>
  </div>
  <div class="stat-card">
    <div class="stat-number">2.5x</div>
    <div class="stat-label">Speed Increase</div>
  </div>
</div>
```

---

## 11. Before/After Slider

Interactive drag-to-compare component with auto-animation.

```css
.ba-slider {
  position: relative; overflow: hidden;
  border-radius: 12px; cursor: col-resize;
  user-select: none; aspect-ratio: 3/4;
}
.ba-slider img {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover; pointer-events: none;
}
.ba-before-clip {
  position: absolute; inset: 0; z-index: 1;
  will-change: clip-path;
}
.ba-divider {
  position: absolute; top: 0; bottom: 0;
  z-index: 3; pointer-events: none;
}
.ba-divider-line {
  position: absolute; inset: 0; width: 1px;
  background: rgba(255,255,255,0.8);
  box-shadow: 0 0 8px rgba(0,0,0,0.6);
}
.ba-handle {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 36px; height: 36px; border-radius: 50%;
  background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center;
}
.ba-label {
  position: absolute; top: 12px; z-index: 4;
  font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase;
  color: rgba(255,255,255,0.8);
  background: rgba(0,0,0,0.4); backdrop-filter: blur(8px);
  padding: 3px 10px; border-radius: 3px;
}
.ba-label-before { left: 12px; }
.ba-label-after { right: 12px; }
```

```html
<div class="ba-slider">
  <img src="after.jpg" alt="After">
  <div class="ba-before-clip">
    <img src="before.jpg" alt="Before">
  </div>
  <div class="ba-divider">
    <div class="ba-divider-line"></div>
    <div class="ba-handle">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
    </div>
  </div>
  <span class="ba-label ba-label-before">Before</span>
  <span class="ba-label ba-label-after">After</span>
</div>
```

**JS** (drag + auto-animation):

```js
document.querySelectorAll('.ba-slider').forEach(function(slider) {
  var position = 50, isDragging = false;
  var beforeClip = slider.querySelector('.ba-before-clip');
  var divider = slider.querySelector('.ba-divider');

  function updatePosition(pct) {
    position = Math.min(Math.max(pct, 0), 100);
    beforeClip.style.clipPath = 'inset(0 ' + (100 - position) + '% 0 0)';
    divider.style.left = position + '%';
  }
  function getPos(clientX) {
    var rect = slider.getBoundingClientRect();
    return ((clientX - rect.left) / rect.width) * 100;
  }

  slider.addEventListener('mousedown', function(e) {
    e.preventDefault(); isDragging = true;
    updatePosition(getPos(e.clientX));
  });
  slider.addEventListener('touchstart', function(e) {
    isDragging = true;
    updatePosition(getPos(e.touches[0].clientX));
  }, { passive: true });
  window.addEventListener('mousemove', function(e) {
    if (isDragging) updatePosition(getPos(e.clientX));
  });
  window.addEventListener('touchmove', function(e) {
    if (isDragging) updatePosition(getPos(e.touches[0].clientX));
  }, { passive: true });
  window.addEventListener('mouseup', function() { isDragging = false; });
  window.addEventListener('touchend', function() { isDragging = false; });

  updatePosition(50);
});
```

---

## 12. Image Grid (2/3/4 columns)

```css
.grid-2col { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
.grid-3col { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.grid-4col { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }

@media (max-width: 900px) {
  .grid-2col { grid-template-columns: 1fr; }
  .grid-3col { grid-template-columns: 1fr; }
  .grid-4col { grid-template-columns: repeat(2, 1fr); }
}
```

Image cards with hover zoom:

```css
.img-card {
  position: relative; overflow: hidden;
  border-radius: 12px; cursor: pointer;
}
.img-card img {
  width: 100%; height: 100%; object-fit: cover;
  transition: transform 0.5s ease-out;
}
.img-card:hover img { transform: scale(1.03); }
```

---

## 13. Lightbox

```css
.lightbox-overlay {
  position: fixed; inset: 0; z-index: 20000;
  background: rgba(0,0,0,0.92);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none;
  transition: opacity 0.3s;
}
.lightbox-overlay.active { opacity: 1; pointer-events: all; }
.lightbox-close {
  position: absolute; top: 1.5rem; right: 1.5rem;
  background: none; border: none; color: white;
  font-size: 2rem; cursor: pointer;
}
.lightbox-img {
  max-width: 90vw; max-height: 85vh;
  object-fit: contain; border-radius: 8px;
}
```

```html
<div class="lightbox-overlay" id="lightbox">
  <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
  <img class="lightbox-img" id="lightboxImg" src="" alt="">
</div>
```

```js
function openLightbox(src) {
  document.getElementById('lightboxImg').src = src;
  document.getElementById('lightbox').classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('active');
  document.body.style.overflow = '';
}
document.getElementById('lightbox').addEventListener('click', function(e) {
  if (e.target === this) closeLightbox();
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeLightbox();
});
```

---

## 14. Pipeline Flow

```css
.pipeline-flow {
  display: flex; align-items: center;
  gap: 0.75rem; flex-wrap: wrap;
}
.pipeline-step {
  border-radius: 12px; padding: 0.85rem 1.5rem;
  font-size: 1rem; font-weight: 500;
  white-space: nowrap;
  display: inline-flex; align-items: center; gap: 0.5rem;
}
.pipeline-arrow { color: #444; font-size: 1.4rem; }
```

```html
<div class="pipeline-flow fade-up">
  <div class="pipeline-step" style="background: rgba(74,222,128,0.08); border: 1px solid rgba(74,222,128,0.2); color: #4ADE80;">
    Step 1: Analyze
  </div>
  <span class="pipeline-arrow">&rarr;</span>
  <div class="pipeline-step" style="background: rgba(34,211,238,0.08); border: 1px solid rgba(34,211,238,0.2); color: #22D3EE;">
    Step 2: Generate
  </div>
  <span class="pipeline-arrow">&rarr;</span>
  <div class="pipeline-step" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);">
    Step 3: Validate
  </div>
</div>
```

---

## 15. Status Badges

```css
.case-badge {
  display: inline-block;
  font-size: 0.65rem; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  padding: 0.3rem 0.9rem; border-radius: 6px;
  margin-bottom: 1rem;
}
.case-badge.released {
  background: rgba(74,222,128,0.1); color: #4ADE80;
}
.case-badge.progress {
  background: rgba(34,211,238,0.1); color: #22D3EE;
}
.case-badge.planned {
  background: rgba(255,255,255,0.05); color: var(--text-muted);
}
```

```html
<span class="case-badge released">Released</span>
<span class="case-badge progress">In Progress</span>
<span class="case-badge planned">Planned</span>
```

---

## 16. As-Is / To-Be Cards

```css
@keyframes asis-pulse {
  0%, 100% { border-color: rgba(248,113,113,0.12); }
  50% { border-color: rgba(248,113,113,0.3); box-shadow: 0 0 16px rgba(248,113,113,0.06); }
}
@keyframes tobe-glow {
  0%, 100% { border-color: rgba(74,222,128,0.15); }
  50% { border-color: rgba(74,222,128,0.35); box-shadow: 0 0 18px rgba(74,222,128,0.08); }
}
.asis-card { animation: asis-pulse 4s ease-in-out infinite; }
.tobe-card { animation: tobe-glow 4s ease-in-out infinite; }
```

```html
<div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 1.5rem; align-items: center;">
  <div class="card asis-card" style="border-color: rgba(248,113,113,0.2);">
    <span class="case-badge" style="background: rgba(248,113,113,0.1); color: #F87171;">AS-IS</span>
    <p>Current state description</p>
  </div>
  <div style="font-size: 2rem; color: var(--text-muted);">&rarr;</div>
  <div class="card tobe-card" style="border-color: rgba(74,222,128,0.2);">
    <span class="case-badge released">TO-BE</span>
    <p>Target state description</p>
  </div>
</div>
```

---

## 17. Quote / Callout

```css
.callout {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 1.5rem 1.75rem;
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
.callout-border {
  padding: 1rem 1.5rem;
  border-left: 3px solid var(--accent-purple);
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.7;
}
```

```html
<div class="callout fade-up">
  <strong>Key Insight:</strong> Important message here.
</div>

<div class="callout-border fade-up">
  <strong>Note:</strong> Highlighted insight with left border accent.
</div>
```

---

## 18. Timeline

```css
.timeline {
  position: relative;
  padding-left: 2rem;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: var(--border-subtle);
}
.timeline-item {
  position: relative;
  padding-bottom: 2.5rem;
  padding-left: 2rem;
}
.timeline-dot {
  position: absolute;
  left: -2.55rem; top: 0.3rem;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--accent-good);
  box-shadow: 0 0 0 4px var(--bg-primary);
}
.timeline-date {
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.timeline-content h4 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}
.timeline-content p {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.7;
}
```

```html
<div class="timeline fade-up">
  <div class="timeline-item">
    <div class="timeline-dot"></div>
    <div class="timeline-date">Q1 2026</div>
    <div class="timeline-content">
      <h4>Phase 1: Foundation</h4>
      <p>Core infrastructure and initial workflows.</p>
    </div>
  </div>
  <div class="timeline-item">
    <div class="timeline-dot" style="background: var(--accent-purple);"></div>
    <div class="timeline-date">Q2 2026</div>
    <div class="timeline-content">
      <h4>Phase 2: Expansion</h4>
      <p>Additional workflows and brand coverage.</p>
    </div>
  </div>
</div>
```

---

## 19. Back to Top Button

```css
.back-to-top {
  position: fixed;
  bottom: 2rem; right: 2rem;
  z-index: 9999;
  width: 48px; height: 48px;
  border: 1px solid var(--border-subtle);
  background: rgba(26, 26, 26, 0.9);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transform: translateY(10px);
  transition: all 0.3s;
}
.back-to-top.visible { opacity: 1; transform: translateY(0); }
.back-to-top:hover { border-color: var(--border-hover); color: var(--text-primary); }
```

```html
<button class="back-to-top" id="backToTop"
  onclick="window.scrollTo({top:0,behavior:'smooth'})" aria-label="Back to top">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
</button>
```

```js
window.addEventListener('scroll', function() {
  var btn = document.getElementById('backToTop');
  btn.classList.toggle('visible', window.scrollY > 600);
}, { passive: true });
```

---

## 20. SVG Architecture Diagram

For complex flow diagrams, use inline SVG. Key patterns:

```html
<div style="background: #111; border-radius: 16px; padding: 2rem; overflow-x: auto;">
  <svg viewBox="0 0 1200 400" xmlns="http://www.w3.org/2000/svg">
    <!-- Background grid -->
    <defs>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <line x1="0" y1="40" x2="40" y2="40" stroke="rgba(255,255,255,0.04)" />
        <line x1="40" y1="0" x2="40" y2="40" stroke="rgba(255,255,255,0.04)" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#grid)" />

    <!-- Nodes -->
    <rect x="50" y="150" width="200" height="100" rx="12"
      fill="rgba(255,255,255,0.025)" stroke="rgba(255,255,255,0.08)" />
    <text x="150" y="195" text-anchor="middle" fill="#FAFAFA" font-size="14">Node Label</text>

    <!-- Connecting arrows -->
    <line x1="250" y1="200" x2="350" y2="200"
      stroke="rgba(255,255,255,0.15)" stroke-width="1" />
  </svg>
</div>
```

---

## 21. Footer

```css
.footer {
  border-top: 1px solid var(--border-subtle);
  padding: 5rem 0;
  text-align: center;
}
.footer-brand {
  font-size: 0.9rem; font-weight: 500;
  letter-spacing: 0.12em; color: var(--text-secondary);
}
.footer-note {
  font-size: 0.8rem; color: var(--text-muted);
  letter-spacing: 0.12em;
}
```

```html
<footer class="footer">
  <div class="container">
    <p class="footer-brand">Organization Name</p>
    <p class="footer-note">Report Title &middot; 2026</p>
  </div>
</footer>
```

---

## Print Support

Always include basic print styles:

```css
@media print {
  .navbar, .scroll-progress, .back-to-top, .theme-toggle { display: none !important; }
  .hero { height: auto; min-height: auto; page-break-after: always; }
  .fade-up { opacity: 1 !important; transform: none !important; }
  body { background: white; color: black; }
  section { page-break-inside: avoid; }
}
```
