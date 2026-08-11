import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/question.dart';
import '../models/history.dart';

class ApiConfig {
  /// Override at run time, e.g.:
  /// `flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000`
  static const String _envUrl = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_envUrl.isNotEmpty) return _envUrl;
    return 'https://103-181-177-31.nip.io';
  }
}

class ApiService {
  String get _baseUrl => ApiConfig.baseUrl;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
      };

  Future<List<Map<String, dynamic>>> getSubjects() async {
    final response = await http.get(
      Uri.parse('$_baseUrl/api/subjects'),
      headers: _headers,
    );
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load subjects: ${response.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getSyllabus(String subject, {String? unit}) async {
    final encodedSubject = Uri.encodeComponent(subject);
    final uri = Uri.parse('$_baseUrl/api/syllabus/$encodedSubject').replace(
      queryParameters: {
        if (unit != null && unit.isNotEmpty) 'unit': unit,
      },
    );
    final response = await http.get(uri, headers: _headers);
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load syllabus: ${response.statusCode}');
    }
  }

  /// Podhu Tamil units menu — server-driven (`backend/tamil_units.json`).
  Future<List<Map<String, dynamic>>> getTamilUnits() async {
    final response = await http.get(
      Uri.parse('$_baseUrl/api/tamil/units'),
      headers: _headers,
    );
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load Tamil units: ${response.statusCode}');
    }
  }

  Future<List<Question>> getQuestions({
    required String subject,
    String? topic,
    String? batch,
  }) async {
    var uri = Uri.parse('$_baseUrl/api/questions').replace(
      queryParameters: {
        'subject': subject,
        if (topic != null) 'topic': topic,
        if (batch != null) 'batch': batch,
      },
    );
    final response = await http.get(uri, headers: _headers);
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.map((q) => Question.fromJson(q)).toList();
    } else {
      throw Exception('Failed to load questions: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> calculateStats(List<HistoryEntry> history) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/stats'),
      headers: _headers,
      body: jsonEncode(history.map((h) => h.toJson()).toList()),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else {
      throw Exception('Failed to fetch stats: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> submitSession({
    required String userId,
    required String topicName,
    required int correctCount,
    required int totalCount,
    required int timeTaken,
    required List<Map<String, dynamic>> answers,
    String? batch,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/sessions/submit'),
      headers: _headers,
      body: jsonEncode({
        'user_id': userId,
        'topic_name': topicName,
        'correct_count': correctCount,
        'total_count': totalCount,
        'time_taken': timeTaken,
        'answers': answers,
        if (batch != null && batch.isNotEmpty) 'batch': batch,
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else {
      throw Exception('Failed to submit session: ${response.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getUserHistory(String userId) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/api/sessions/history?user_id=$userId'),
      headers: _headers,
    );
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load user history: ${response.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getCompletedBatches({
    required String userId,
    required String topic,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/sessions/completed-batches').replace(
      queryParameters: {
        'user_id': userId,
        'topic': topic,
      },
    );
    final response = await http.get(uri, headers: _headers);
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load completed batches: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> getSessionDetail({
    required String userId,
    required int sessionId,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/sessions/$sessionId').replace(
      queryParameters: {'user_id': userId},
    );
    final response = await http.get(uri, headers: _headers);
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load session detail: ${response.statusCode}');
    }
  }

  Future<void> deleteAccount(String userId) async {
    final response = await http.delete(
      Uri.parse('$_baseUrl/api/users/$userId'),
      headers: _headers,
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to delete account: ${response.statusCode}');
    }
  }

  /// Fire-and-forget analytics event logging. Failures are swallowed so
  /// that analytics never impacts the user-facing experience.
  Future<void> logEvent(String userId, String eventType, [Map<String, dynamic>? metaData]) async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/api/events'),
        headers: _headers,
        body: jsonEncode({
          'user_id': userId,
          'event_type': eventType,
          'meta_data': metaData ?? {},
        }),
      );
    } catch (e) {
      debugPrint('logEvent($eventType) failed silently: $e');
    }
  }

  Future<void> updateDeviceInfo({
    required String userId,
    String? displayName,
  }) async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/api/users/device-info'),
        headers: _headers,
        body: jsonEncode({
          'user_id': userId,
          if (displayName != null) 'display_name': displayName,
        }),
      );
    } catch (e) {
      debugPrint('updateDeviceInfo failed silently: $e');
    }
  }
}
