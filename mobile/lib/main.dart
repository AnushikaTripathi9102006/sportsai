import 'package:flutter/material.dart';

import 'core/config/app_config.dart';
import 'core/theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SportsAiApp());
}

class SportsAiApp extends StatelessWidget {
  const SportsAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SportsAI',
      theme: AppTheme.light,
      home: const Scaffold(
        body: Center(
          child: Text('SportsAI mobile app'),
        ),
      ),
    );
  }
}
