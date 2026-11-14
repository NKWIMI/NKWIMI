import 'package:flutter/material.dart';

import '../l10n/l10n.dart';
import '../services/account_service.dart';
import '../services/screening_engine.dart';
import '../theme.dart';
import 'result_screen.dart';

/// Two-step check: 1) possible exposure, 2) symptoms.
class ScreeningScreen extends StatefulWidget {
  const ScreeningScreen({super.key});

  @override
  State<ScreeningScreen> createState() => _ScreeningScreenState();
}

class _ScreeningScreenState extends State<ScreeningScreen> {
  final Map<String, bool> _answers = {};
  int _step = 0;

  static const _steps = [
    ('scr_s1_title', 'scr_s1_hint', ScreeningEngine.exposureQuestions),
    ('scr_s2_title', 'scr_s2_hint', ScreeningEngine.symptomQuestions),
  ];

  void _next() {
    if (_step < _steps.length - 1) {
      setState(() => _step++);
    } else {
      final result = ScreeningEngine.evaluate(_answers);
      AccountService.recordCheck(); // only a counter – answers are not stored
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => ResultScreen(result: result)),
      );
    }
  }

  void _back() {
    if (_step > 0) {
      setState(() => _step--);
    } else {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final (titleKey, hintKey, questions) = _steps[_step];
    final title = tr(titleKey), hint = tr(hintKey);
    final text = Theme.of(context).textTheme;
    final last = _step == _steps.length - 1;
    final selected = questions.where((q) => _answers[q.id] ?? false).length;

    return PopScope(
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(tr('scr_title')),
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(6),
            child: LinearProgressIndicator(
              value: (_step + 1) / _steps.length,
              minHeight: 6,
            ),
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          children: [
            Text(tr('scr_step', {'a': '${_step + 1}', 'b': '${_steps.length}'}),
                style: text.labelLarge
                    ?.copyWith(color: Theme.of(context).colorScheme.primary)),
            const SizedBox(height: 4),
            Text(title, style: text.headlineSmall),
            const SizedBox(height: 6),
            Text(hint),
            const SizedBox(height: 16),
            for (final q in questions)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _QuestionCard(
                  question: q,
                  selected: _answers[q.id] ?? false,
                  onChanged: (v) => setState(() => _answers[q.id] = v),
                ),
              ),
          ],
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: Row(children: [
              if (_step > 0) ...[
                Expanded(
                  child: OutlinedButton(
                      onPressed: _back, child: Text(tr('back'))),
                ),
                const SizedBox(width: 12),
              ],
              Expanded(
                flex: 2,
                child: FilledButton(
                  onPressed: _next,
                  child: Text(last
                      ? tr('scr_see_result')
                      : selected == 0
                          ? tr('scr_none_next')
                          : tr('next')),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  const _QuestionCard({
    required this.question,
    required this.selected,
    required this.onChanged,
  });

  final ScreeningQuestion question;
  final bool selected;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: selected ? Brand.primary : scheme.outlineVariant,
          width: selected ? 2 : 1,
        ),
        color: selected ? Brand.primary.withValues(alpha: 0.08) : scheme.surface,
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () => onChanged(!selected),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                selected ? Icons.check_circle : Icons.radio_button_unchecked,
                color: selected ? Brand.primary : scheme.outline,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(question.text,
                        style: const TextStyle(fontSize: 15.5, height: 1.35)),
                    if (question.help != null) ...[
                      const SizedBox(height: 4),
                      Text(question.help!,
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
