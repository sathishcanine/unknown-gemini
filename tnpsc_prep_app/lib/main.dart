import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';

import 'providers/app_state.dart';
import 'screens/home_screen.dart';
import 'screens/syllabus_screen.dart';
import 'screens/topic_detail_screen.dart';
import 'screens/quiz_screen.dart';
import 'screens/results_screen.dart';
import 'screens/advisor_screen.dart';
import 'screens/login_screen.dart';
import 'screens/performance_screen.dart';
import 'screens/profile_screen.dart';
import 'services/update_service.dart';
import 'widgets/update_dialog.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint('Firebase initialization failed: $e');
  }

  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState(),
      child: const TNPSCPrepApp(),
    ),
  );
}

class TNPSCPrepApp extends StatelessWidget {
  const TNPSCPrepApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    return MaterialApp(
      title: 'ACE TNPSC Unlimited Questions',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.light().copyWith(
        scaffoldBackgroundColor: const Color(0xFFF1F5F9),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFFF1F5F9),
          elevation: 0,
          iconTheme: IconThemeData(color: Color(0xFF0F172A)),
          titleTextStyle: TextStyle(color: Color(0xFF0F172A), fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ),
      darkTheme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0B0F19),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0B0F19),
          elevation: 0,
          iconTheme: IconThemeData(color: Colors.white),
          titleTextStyle: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ),
      themeMode: appState.isDarkMode ? ThemeMode.dark : ThemeMode.light,
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({Key? key}) : super(key: key);

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _updateCheckStarted = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkForUpdate());
  }

  Future<void> _checkForUpdate() async {
    if (_updateCheckStarted) return;
    _updateCheckStarted = true;

    final info = await UpdateService().checkForUpdate();
    if (info == null || !mounted) return;

    final isDarkMode = Provider.of<AppState>(context, listen: false).isDarkMode;
    UpdateDialog.show(context, info, isDarkMode: isDarkMode);
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);

    // Hold splash until SharedPreferences session is restored — avoids Login flash.
    if (!appState.authReady) {
      return const _AuthBootstrapScreen();
    }

    if (!appState.isAuthenticated) {
      return const LoginScreen();
    }
    
    final active = appState.activeScreen;

    int currentIndex = 0;
    if (active == 'home' || active == 'topic_detail' || active == 'results' || active == 'syllabus') {
      currentIndex = 0;
    } else if (active == 'performance') {
      currentIndex = 1;
    } else if (active == 'advisor') {
      currentIndex = 2;
    }

    Widget body;
    if (active == 'home') {
      body = const HomeScreen();
    } else if (active == 'syllabus') {
      body = const SyllabusScreen();
    } else if (active == 'topic_detail') {
      body = const TopicDetailScreen();
    } else if (active == 'quiz') {
      body = const QuizScreen();
    } else if (active == 'results') {
      body = const ResultsScreen();
    } else if (active == 'advisor') {
      body = const AdvisorScreen();
    } else if (active == 'performance') {
      body = const PerformanceScreen();
    } else if (active == 'profile') {
      body = const ProfileScreen();
    } else {
      body = const HomeScreen();
    }

    // Profile is opened from home settings; hide bottom nav there (and during quiz).
    final showBottomNav = active != 'quiz' && active != 'profile';
    final isDark = appState.isDarkMode;

    return Scaffold(
      body: body,
      bottomNavigationBar: showBottomNav
          ? BottomNavigationBar(
              type: BottomNavigationBarType.fixed,
              backgroundColor: isDark ? const Color(0xFF131A2A) : Colors.white,
              selectedItemColor: const Color(0xFF3B82F6),
              unselectedItemColor: isDark ? Colors.grey : const Color(0xFF64748B),
              currentIndex: currentIndex,
              onTap: (index) {
                if (index == 0) {
                  appState.navigateToHome();
                } else if (index == 1) {
                  appState.navigateToPerformance();
                } else if (index == 2) {
                  appState.navigateToAdvisor();
                }
              },
              items: const [
                BottomNavigationBarItem(
                  icon: Icon(Icons.home),
                  label: 'Home',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.bar_chart),
                  label: 'Performance',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.assistant),
                  label: 'AI Advisor',
                ),
              ],
            )
          : null,
    );
  }
}

/// Matches native splash while auth session is restored from local storage.
class _AuthBootstrapScreen extends StatelessWidget {
  const _AuthBootstrapScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFF0B0F19),
      body: Center(
        child: Image(
          image: AssetImage('assets/icon/app_icon.png'),
          width: 120,
          height: 120,
        ),
      ),
    );
  }
}
