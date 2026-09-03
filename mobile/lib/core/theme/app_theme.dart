import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF176B87),
        brightness: Brightness.light,
      ),
      useMaterial3: true,
    );
  }
}
