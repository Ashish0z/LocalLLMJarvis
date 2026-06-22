# Local LLM Jarvis Android

Android MVP client for the local assistant.

## Requirements

Install:

- Android Studio.
- Android SDK platform for the configured `compileSdk`.
- An Android emulator or physical Android phone.
- Tailscale on the phone for private-network access to the backend.

The project uses Kotlin and Jetpack Compose. Android Studio should install or sync the required Gradle and Android plugin dependencies.

## Open in Android Studio

1. Open the `android` folder in Android Studio.
2. Let Android Studio sync Gradle dependencies.
3. Run the `app` configuration on an emulator or physical Android device.

If Android Studio asks to create `local.properties`, allow it. That file should point to your local Android SDK and is intentionally ignored by Git.

## API URL

The app defaults to:

- `http://10.0.2.2:8000` for Android Emulator access to the host machine.

For a physical phone on Tailscale, set the API URL in the app Settings section, for example:

- `http://your-tailscale-hostname:8000`
- `http://100.x.y.z:8000`

Before testing on a physical phone:

1. Start the backend with Docker Compose from the repo root:

   ```powershell
   docker compose up --build api postgres ollama
   ```

2. Sign in to Tailscale on the server machine and phone.
3. Get the server Tailscale IP:

   ```powershell
   tailscale ip -4
   ```

4. In the Android app, set the API URL:

   ```text
   http://100.x.y.z:8000
   ```

## MVP Scope

- Today screen from `/today`.
- Text capture through `/assistant/message`.
- Voice capture using Android speech recognition.
- Task completion through `/tasks/{id}`.
- Manual API URL configuration.

## Build a Debug APK

Use Android Studio:

1. Open the `android` folder.
2. Wait for Gradle sync to finish.
3. Select `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
4. Click `locate` after the build completes.

Expected output:

```text
android\app\build\outputs\apk\debug\app-debug.apk
```

Install the debug APK on a connected device:

```powershell
adb install -r android\app\build\outputs\apk\debug\app-debug.apk
```

If `adb` is not in PATH, use Android Studio's Device Manager or find it under your Android SDK `platform-tools` directory.

## Build a Signed Release APK

Use Android Studio:

1. Select `Build > Generate Signed Bundle / APK`.
2. Select `APK`.
3. Create a new keystore or choose an existing one.
4. Choose the `release` build variant.
5. Finish the wizard.

Store the keystore and passwords safely. Future updates to the same app must be signed with the same key.

## Emulator Networking

Use this API URL in the app when testing on the Android Emulator:

```text
http://10.0.2.2:8000
```

`10.0.2.2` is the emulator's route back to the host computer.

## Physical Device Networking

Use Tailscale for the intended private-network setup.

1. Connect the phone to Tailscale.
2. Confirm the server is visible in the Tailscale app.
3. Set the app API URL to the server's Tailscale IP or MagicDNS name.

Examples:

```text
http://100.x.y.z:8000
http://your-machine-name:8000
```

## Troubleshooting

- If Today does not load, check `http://localhost:8000/health` on the server.
- If the emulator cannot connect, confirm the app URL is `http://10.0.2.2:8000`.
- If a physical phone cannot connect, confirm both devices are signed in to Tailscale.
- If voice capture fails, grant microphone permission to the app.
- If Android Studio sync fails, install the SDK version requested by the project.

