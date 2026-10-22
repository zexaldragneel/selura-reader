#!/usr/bin/env bash
# Run only against an isolated disposable CI emulator. No user content is read.
set -euo pipefail

PACKAGE="com.selura.manga"
APK="selura-manga.apk"
mkdir -p emulator-evidence
test -s "$APK"

adb wait-for-device
adb shell getprop sys.boot_completed | tr -d '\r' | grep -x 1
adb install -r "$APK" | tee emulator-evidence/install.log
adb shell pm path "$PACKAGE" | tee emulator-evidence/package-path.txt | grep -F "$PACKAGE"
adb shell dumpsys package "$PACKAGE" > emulator-evidence/package-info.txt
grep -F "versionCode=1088" emulator-evidence/package-info.txt

check_app_crash() {
  local mode="$1"
  adb logcat -d -v threadtime > "emulator-evidence/logcat-$mode.txt"
  # An unrelated system app may crash; only fail for Selura's process.
  if grep -A 18 'FATAL EXCEPTION:' "emulator-evidence/logcat-$mode.txt" |
    grep -E 'Process: com\.selura\.manga(,|$)'; then
    echo "Selura application crashed during $mode launch" >&2
    exit 1
  fi
  adb shell pidof "$PACKAGE" | tr -d '\r' | grep -E '^[0-9]+( [0-9]+)*$'
  adb exec-out screencap -p > "emulator-evidence/$mode.png"
  test -s "emulator-evidence/$mode.png"
}

adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 |
  tee emulator-evidence/launch-online.txt | grep -F "Events injected: 1"
sleep 20
check_app_crash online

# Cold launch with radios disabled tests app boot, not downloaded pages.
# It does not simulate real chapter content or source authentication.
adb shell svc wifi disable
adb shell svc data disable
adb shell am force-stop "$PACKAGE"
adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 |
  tee emulator-evidence/launch-radios-disabled.txt | grep -F "Events injected: 1"
sleep 15
check_app_crash radios-disabled

echo "Build 88: installed, launched online and with radios disabled; no Selura FATAL exception or process termination found." |
  tee emulator-evidence/result.txt
