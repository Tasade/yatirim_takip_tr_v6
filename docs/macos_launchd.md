# macOS launchd (opsiyonel)

`~/Library/LaunchAgents/com.tasade.yatirim.service.plist` örnek:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.tasade.yatirim.service</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>/PATH/yatirim_takip_tr_v5/service/run_service.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>WorkingDirectory</key><string>/PATH/yatirim_takip_tr_v5</string>
  <key>StandardOutPath</key><string>/PATH/yatirim_takip_tr_v5/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>/PATH/yatirim_takip_tr_v5/logs/launchd.err</string>
</dict>
</plist>
```
