#!/usr/bin/env python3
"""
Notification Hook: Windows 알림
Claude가 입력 대기 중일 때 Windows 토스트 알림 표시
"""
import json
import sys
import subprocess
import os

def show_windows_toast(title, message):
    """Windows 토스트 알림 표시 (PowerShell 사용)"""
    ps_script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @"
    <toast>
        <visual>
            <binding template="ToastText02">
                <text id="1">{title}</text>
                <text id="2">{message}</text>
            </binding>
        </visual>
        <audio silent="true"/>
    </toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code")
    $notifier.Show($toast)
    '''

    try:
        subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            timeout=5
        )
    except Exception:
        # 알림 실패해도 무시
        pass

def show_simple_beep():
    """간단한 비프음 (토스트 실패 시 폴백)"""
    try:
        import winsound
        winsound.Beep(800, 200)  # 800Hz, 200ms
    except Exception:
        pass

def main():
    try:
        input_data = json.load(sys.stdin)

        # 알림 타입에 따라 메시지 설정
        notification_type = input_data.get('type', 'input_required')
        message = input_data.get('message', 'Claude Code에서 입력을 기다리고 있습니다.')

        if notification_type == 'input_required':
            title = "Claude Code"
            msg = "입력을 기다리고 있습니다"
        elif notification_type == 'permission_required':
            title = "Claude Code - 권한 요청"
            msg = "작업 승인이 필요합니다"
        elif notification_type == 'task_complete':
            title = "Claude Code"
            msg = "작업이 완료되었습니다"
        else:
            title = "Claude Code"
            msg = message[:50] if message else "알림"

        # Windows 환경 체크
        if os.name == 'nt':
            show_windows_toast(title, msg)
        else:
            # Linux/Mac은 단순 출력
            print(f"[{title}] {msg}", file=sys.stderr)

    except Exception:
        pass

    sys.exit(0)

if __name__ == '__main__':
    main()
