#!/bin/sh
# Build the Android app (debug APK). Pass --install to put it on a USB-connected phone.
set -e
cd "$(dirname "$0")/web"
. "$HOME/.config/android-env.zsh"
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home   # Capacitor needs Java 21
npm run build
npx cap sync android
(cd android && ./gradlew assembleDebug -q)
APK="$PWD/android/app/build/outputs/apk/debug/app-debug.apk"
echo "APK: $APK"
[ "$1" = "--install" ] && adb install -r "$APK"
exit 0
