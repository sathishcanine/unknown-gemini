class Option {
  final String key;
  final String textEn;
  final String textTa;

  Option({
    required this.key,
    required this.textEn,
    required this.textTa,
  });

  factory Option.fromJson(Map<String, dynamic> json) {
    return Option(
      key: json['key'] ?? '',
      textEn: json['text_en'] ?? '',
      textTa: json['text_ta'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'key': key,
      'text_en': textEn,
      'text_ta': textTa,
    };
  }
}

class Question {
  final int? id;
  final String subject;
  final String topic;
  final String sourceExam;
  final String difficulty;
  final String questionEn;
  final String questionTa;
  final List<Option> options;
  final String correctOption;
  final String explanation;
  final String explanationTa;
  final String type;
  final String batch;
  final String group;
  final String sourceFact;

  Question({
    this.id,
    required this.subject,
    required this.topic,
    required this.sourceExam,
    required this.difficulty,
    required this.questionEn,
    required this.questionTa,
    required this.options,
    required this.correctOption,
    required this.explanation,
    required this.explanationTa,
    required this.type,
    required this.batch,
    required this.group,
    required this.sourceFact,
  });

  factory Question.fromJson(Map<String, dynamic> json) {
    var rawOpts = json['options'] as List? ?? [];
    return Question(
      id: json['id'] != null ? int.tryParse(json['id'].toString()) : null,
      subject: json['subject'] ?? '',
      topic: json['topic'] ?? '',
      sourceExam: json['source_exam'] ?? '',
      difficulty: json['difficulty'] ?? 'Medium',
      questionEn: json['question_en'] ?? '',
      questionTa: json['question_ta'] ?? '',
      options: rawOpts.map((o) => Option.fromJson(o)).toList(),
      correctOption: json['correct_option'] ?? '',
      explanation: json['explanation'] ?? '',
      explanationTa: json['explanation_ta'] ?? '',
      type: json['type'] ?? '',
      batch: json['batch'] ?? '',
      group: json['group'] ?? '',
      sourceFact: json['source_fact'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'subject': subject,
      'topic': topic,
      'source_exam': sourceExam,
      'difficulty': difficulty,
      'question_en': questionEn,
      'question_ta': questionTa,
      'options': options.map((o) => o.toJson()).toList(),
      'correct_option': correctOption,
      'explanation': explanation,
      'explanation_ta': explanationTa,
      'type': type,
      'batch': batch,
      'group': group,
      'source_fact': sourceFact,
    };
  }
}
