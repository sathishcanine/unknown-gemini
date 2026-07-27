import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/question.dart';
import '../models/history.dart';

class ApiConfig {
  static String get baseUrl {
    return "http://103.181.177.31:8085";
  }
}

class ApiService {
  final String _baseUrl = ApiConfig.baseUrl;

  Future<List<Map<String, dynamic>>> getSubjects() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/subjects'));
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load subjects: ${response.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getSyllabus(String subject) async {
    final encodedSubject = Uri.encodeComponent(subject);
    final response = await http.get(Uri.parse('$_baseUrl/api/syllabus/$encodedSubject'));
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load syllabus: ${response.statusCode}');
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
    final response = await http.get(uri);
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
      headers: {'Content-Type': 'application/json'},
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
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/sessions/submit'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'topic_name': topicName,
        'correct_count': correctCount,
        'total_count': totalCount,
        'time_taken': timeTaken,
        'answers': answers,
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else {
      throw Exception('Failed to submit session: ${response.statusCode}');
    }
  }

  Future<List<Map<String, dynamic>>> getUserHistory(String userId) async {
    final response = await http.get(Uri.parse('$_baseUrl/api/sessions/history?user_id=$userId'));
    if (response.statusCode == 200) {
      List data = jsonDecode(utf8.decode(response.bodyBytes));
      return data.cast<Map<String, dynamic>>();
    } else {
      throw Exception('Failed to load user history: ${response.statusCode}');
    }
  }
}
