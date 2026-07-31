import 'question.dart';

class HistoryEntry {
  final String topic;
  final String group;
  final int correctCount;
  final int totalCount;
  final Map<String, String> answers; // qIndexStr -> selectedOption
  final List<Question> questions;
  final double timestamp;
  final String batch;

  HistoryEntry({
    required this.topic,
    required this.group,
    required this.correctCount,
    required this.totalCount,
    required this.answers,
    required this.questions,
    required this.timestamp,
    this.batch = '',
  });

  factory HistoryEntry.fromJson(Map<String, dynamic> json) {
    var rawAnswers = json['answers'] as Map? ?? {};
    var rawQs = json['questions'] as List? ?? [];
    final questions = rawQs.map((q) => Question.fromJson(q)).toList();
    String batch = (json['batch'] ?? '').toString();
    if (batch.isEmpty) {
      for (final q in questions) {
        if (q.type.toLowerCase() != 'pyq' && q.batch.trim().isNotEmpty) {
          batch = q.batch;
          break;
        }
      }
    }
    return HistoryEntry(
      topic: json['topic'] ?? '',
      group: json['group'] ?? '',
      correctCount: json['correctCount'] ?? 0,
      totalCount: json['totalCount'] ?? 0,
      answers: rawAnswers.map((k, v) => MapEntry(k.toString(), v.toString())),
      questions: questions,
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? DateTime.now().millisecondsSinceEpoch.toDouble(),
      batch: batch,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'topic': topic,
      'group': group,
      'correctCount': correctCount,
      'totalCount': totalCount,
      'answers': answers,
      'questions': questions.map((q) => q.toJson()).toList(),
      'timestamp': timestamp,
      'batch': batch,
    };
  }
}
