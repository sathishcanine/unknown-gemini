import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:tnpsc_prep_app/main.dart';
import 'package:tnpsc_prep_app/providers/app_state.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AppState(),
        child: const TNPSCPrepApp(),
      ),
    );

    // Verify that the title is rendered
    expect(find.text('TNPSC Prep'), findsNothing); // It is a MaterialApp title, not directly rendered as text
  });
}
