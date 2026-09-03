# SportsAI Mobile

Flutter client for the existing SportsAI Django API.

## API URL

The default Android emulator URL is:

```text
http://10.0.2.2:8000/api/v1
```

Override it with:

```text
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

For a physical Android device, use the development computer's LAN IP address and make Django reachable on the local network.

The current scaffold contains only the application shell, API configuration, token storage, and HTTP client. Screens and authentication state will be added incrementally.
