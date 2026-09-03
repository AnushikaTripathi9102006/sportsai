import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import '../storage/token_storage.dart';

class ApiClient {
  ApiClient({http.Client? client, TokenStorage? tokenStorage})
      : _client = client ?? http.Client(),
        _tokenStorage = tokenStorage ?? const TokenStorage();

  final http.Client _client;
  final TokenStorage _tokenStorage;

  Future<http.Response> get(String path) async {
    return _send('GET', path);
  }

  Future<http.Response> post(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _send('POST', path, body: body);
  }

  Future<http.Response> patch(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _send('PATCH', path, body: body);
  }

  Future<http.Response> delete(String path) async {
    return _send('DELETE', path);
  }

  Future<http.Response> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final accessToken = await _tokenStorage.readAccessToken();
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      if (accessToken != null) 'Authorization': 'Bearer $accessToken',
    };
    final uri = Uri.parse('${AppConfig.apiBaseUrl}$path');
    final encodedBody = body == null ? null : jsonEncode(body);

    switch (method) {
      case 'GET':
        return _client.get(uri, headers: headers);
      case 'POST':
        return _client.post(uri, headers: headers, body: encodedBody);
      case 'PATCH':
        return _client.patch(uri, headers: headers, body: encodedBody);
      case 'DELETE':
        return _client.delete(uri, headers: headers);
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }
  }
}
