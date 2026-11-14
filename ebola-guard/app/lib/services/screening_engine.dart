/// Offline, rule-based Ebola screening.
///
/// This follows the public-health logic used by CDC/WHO traveller screening:
/// a person is a concern when they have BOTH a possible exposure in the last
/// 21 days AND compatible symptoms. It does not diagnose anything; only a
/// laboratory test can confirm Ebola. Have a clinician or your Ministry of
/// Health review these questions before release, and adapt them to the
/// current outbreak. Texts live in lib/l10n (keys q_<id>, urgent_*, …).
library;

import '../l10n/l10n.dart';

enum RiskLevel { urgent, monitor, seeDoctor, low }

class ScreeningQuestion {
  const ScreeningQuestion(this.id, {this.hasHelp = false});

  final String id;
  final bool hasHelp;

  String get text => tr('q_$id');
  String? get help => hasHelp ? tr('q_${id}_help') : null;
}

class ScreeningResult {
  const ScreeningResult({
    required this.level,
    required this.title,
    required this.summary,
    required this.actions,
    required this.exposures,
    required this.symptoms,
  });

  final RiskLevel level;
  final String title;
  final String summary;
  final List<String> actions;

  /// Ids of the exposure / symptom questions answered "yes".
  final List<String> exposures;
  final List<String> symptoms;

  /// Short summary given to the AI assistant as context (always in English,
  /// so the model gets the same facts whatever the app language).
  String toChatContext() {
    String names(List<String> ids) =>
        ids.isEmpty ? 'none' : ids.map((id) => trIn('en', 'q_$id')).join('; ');
    return 'Screening result level: ${level.name}\n'
        'Exposures reported: ${names(exposures)}\n'
        'Symptoms reported: ${names(symptoms)}\n';
  }
}

class ScreeningEngine {
  static const exposureQuestions = <ScreeningQuestion>[
    ScreeningQuestion('outbreak_area', hasHelp: true),
    ScreeningQuestion('body_fluids'),
    ScreeningQuestion('cared_for_sick'),
    ScreeningQuestion('funeral'),
    ScreeningQuestion('animals'),
    ScreeningQuestion('survivor_contact'),
  ];

  static const symptomQuestions = <ScreeningQuestion>[
    ScreeningQuestion('fever'),
    ScreeningQuestion('headache'),
    ScreeningQuestion('muscle_pain'),
    ScreeningQuestion('weakness'),
    ScreeningQuestion('sore_throat'),
    ScreeningQuestion('vomiting'),
    ScreeningQuestion('diarrhea'),
    ScreeningQuestion('abdominal_pain'),
    ScreeningQuestion('bleeding'),
  ];

  static ScreeningResult evaluate(Map<String, bool> answers) {
    bool yes(String id) => answers[id] ?? false;

    final exposures = [
      for (final q in exposureQuestions)
        if (yes(q.id)) q.id,
    ];
    final symptoms = [
      for (final q in symptomQuestions)
        if (yes(q.id)) q.id,
    ];

    final exposed = exposures.isNotEmpty;
    final symptomatic = symptoms.isNotEmpty;

    if (exposed && symptomatic) {
      return ScreeningResult(
        level: RiskLevel.urgent,
        title: tr('urgent_title'),
        summary: tr('urgent_summary'),
        actions: [for (var i = 1; i <= 5; i++) tr('urgent_a$i')],
        exposures: exposures,
        symptoms: symptoms,
      );
    }

    if (exposed) {
      return ScreeningResult(
        level: RiskLevel.monitor,
        title: tr('monitor_title'),
        summary: tr('monitor_summary'),
        actions: [for (var i = 1; i <= 4; i++) tr('monitor_a$i')],
        exposures: exposures,
        symptoms: symptoms,
      );
    }

    if (symptomatic) {
      final bleeding = yes('bleeding');
      return ScreeningResult(
        level: RiskLevel.seeDoctor,
        title: tr(bleeding ? 'doctor_title_today' : 'doctor_title'),
        summary: tr('doctor_summary'),
        actions: [
          if (bleeding) tr('doctor_a_bleeding'),
          for (var i = 1; i <= 3; i++) tr('doctor_a$i'),
        ],
        exposures: exposures,
        symptoms: symptoms,
      );
    }

    return ScreeningResult(
      level: RiskLevel.low,
      title: tr('low_title'),
      summary: tr('low_summary'),
      actions: [for (var i = 1; i <= 4; i++) tr('low_a$i')],
      exposures: exposures,
      symptoms: symptoms,
    );
  }
}
