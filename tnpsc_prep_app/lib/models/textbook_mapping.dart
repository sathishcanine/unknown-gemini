class TextbookMapping {
  final String title;
  final String titleTa;
  final String book;
  final String chapter;
  final String pages;
  final String focus;

  TextbookMapping({
    required this.title,
    required this.titleTa,
    required this.book,
    required this.chapter,
    required this.pages,
    required this.focus,
  });

  factory TextbookMapping.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return TextbookMapping(
        title: '',
        titleTa: '',
        book: '',
        chapter: '',
        pages: '',
        focus: '',
      );
    }
    return TextbookMapping(
      title: json['title'] ?? '',
      titleTa: json['titleTa'] ?? '',
      book: json['book'] ?? '',
      chapter: json['chapter'] ?? '',
      pages: json['pages'] ?? '',
      focus: json['focus'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'titleTa': titleTa,
      'book': book,
      'chapter': chapter,
      'pages': pages,
      'focus': focus,
    };
  }
}
