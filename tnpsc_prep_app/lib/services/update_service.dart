import 'package:flutter/foundation.dart';
import 'package:firebase_remote_config/firebase_remote_config.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// How severe the pending update is, decided entirely from Firebase
/// Remote Config values so it can be tuned without shipping a new build.
enum UpdateSeverity { none, soft, force }

class UpdateInfo {
  final UpdateSeverity severity;
  final String title;
  final String message;
  final String updateUrl;
  final String latestVersionName;

  const UpdateInfo({
    required this.severity,
    required this.title,
    required this.message,
    required this.updateUrl,
    required this.latestVersionName,
  });
}

/// Checks whether a newer app version is available by comparing the
/// installed build number (equivalent to Android's BuildConfig.VERSION_CODE)
/// against values published in Firebase Remote Config.
///
/// Remote Config keys used (create these in the Firebase console):
///   minimum_version_code  (Number) - below this, update is forced/blocking.
///   latest_version_code   (Number) - below this, update is optional/soft.
///   latest_version_name   (String) - e.g. "2.3.0", shown to the user.
///   update_title          (String) - dialog title.
///   update_message        (String) - message for optional (soft) updates.
///   force_update_message  (String) - message for mandatory (force) updates.
///   update_url            (String) - optional override; defaults to the
///                                    Play Store listing for this app.
class UpdateService {
  static const String _packageName = 'com.ace.tnpsc.unlimited';
  static const String _defaultStoreUrl =
      'https://play.google.com/store/apps/details?id=$_packageName';

  static const Map<String, dynamic> _defaults = {
    'minimum_version_code': 1,
    'latest_version_code': 1,
    'latest_version_name': '',
    'update_title': 'Update Available',
    'update_message':
        'A new version of TNPSC Prep is available with new features and improvements. Update now for the best experience.',
    'force_update_message':
        'This version of TNPSC Prep is no longer supported. Please update to continue using the app.',
    'update_url': '',
  };

  Future<UpdateInfo?> checkForUpdate() async {
    try {
      final remoteConfig = FirebaseRemoteConfig.instance;

      await remoteConfig.setConfigSettings(
        RemoteConfigSettings(
          fetchTimeout: const Duration(seconds: 10),
          minimumFetchInterval:
              kDebugMode ? Duration.zero : const Duration(hours: 1),
        ),
      );
      await remoteConfig.setDefaults(_defaults);
      await remoteConfig.fetchAndActivate();

      final packageInfo = await PackageInfo.fromPlatform();
      final currentBuildNumber = int.tryParse(packageInfo.buildNumber) ?? 0;

      final minimumVersionCode = remoteConfig.getInt('minimum_version_code');
      final latestVersionCode = remoteConfig.getInt('latest_version_code');
      final latestVersionName = remoteConfig.getString('latest_version_name');
      final configuredUrl = remoteConfig.getString('update_url');
      final updateUrl = configuredUrl.isNotEmpty ? configuredUrl : _defaultStoreUrl;
      final title = remoteConfig.getString('update_title');

      if (currentBuildNumber < minimumVersionCode) {
        return UpdateInfo(
          severity: UpdateSeverity.force,
          title: title,
          message: remoteConfig.getString('force_update_message'),
          updateUrl: updateUrl,
          latestVersionName: latestVersionName,
        );
      }

      if (currentBuildNumber < latestVersionCode) {
        return UpdateInfo(
          severity: UpdateSeverity.soft,
          title: title,
          message: remoteConfig.getString('update_message'),
          updateUrl: updateUrl,
          latestVersionName: latestVersionName,
        );
      }

      return null;
    } catch (e) {
      debugPrint('Update check skipped: $e');
      return null;
    }
  }
}
