import json
import logging
import math
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import gradio as gr

from backend.args import dynamic_args
from modules import script_callbacks, script_loading, scripts, shared
from modules.options import categories


logger = logging.getLogger("anima_lora_stage_scheduler")
LANGUAGE_OPTION = "anima_lora_stage_scheduler_language"
LANGUAGE_CHOICES = ("en", "ko")
LEGACY_LANGUAGE_VALUE = "\x7a\x68"
LANG = {
    "en": {
        "settings_label": "Anima LoRA Stage Scheduler UI language",
        "title": "Anima LoRA Stage Scheduler",
        "enable": "Enable stage scheduling",
        "base_panel": "Base pass",
        "hires_panel": "Hires. fix stage",
        "hires_lora_panel": "Hires. fix LoRA stage",
        "target_scope": "Target scope",
        "panel_weight": "Panel weight, 0 = use prompt / layer-weight plugin",
        "target_lora": "Target LoRA",
        "target_lora_placeholder": "Fill only when target scope is target list; separate multiple names with commas or new lines",
        "template": "Template",
        "copy": "Copy",
        "builder": "Preset combo",
        "auto_timing": "Auto timing from Shift",
        "single_lora_template": "Per-LoRA templates",
        "single_lora_template_placeholder": "One per line: LoRA name=template name\nAlso supports: <lora:name:0.8>=character-feature-stage\nEmpty entries use the template above",
        "start": "Start ratio",
        "end": "End ratio",
        "peak": "Peak ratio",
        "strength": "Stage strength multiplier",
        "curve": "Strength curve",
        "hr_independent": "Use independent Hires. fix panel; disabled = inherit base settings with Hires Shift timing",
        "hr_disable": "Disable LoRA during Hires. fix",
        "hr_disable_tags": "Full LoRA tags to disable",
        "template_manager": "Template management",
        "existing_template": "Existing template",
        "rename_to": "Rename to",
        "rename_template": "Rename template",
        "delete_template": "Delete template",
        "new_template_name": "New template name",
        "save_auto_template": "Save as auto-timing template",
        "save_current_base": "Save current base panel as template",
        "template_help": "### Template Guide",
        "close": "Close",
        "combo_title": "### Preset Combo",
        "template_name": "Template name",
        "base_preset_combo": "Base preset combo",
        "preview_shift": "Preview Shift",
        "save_combo": "Save combo template",
        "combo_current": "Current combo: ",
        "intervention_preview": "Timing preview",
        "table_preset": "Base preset",
        "table_action": "Action",
        "table_start": "Start",
        "table_end": "End",
        "table_peak": "Peak",
        "table_strength": "Strength",
        "table_curve": "Curve",
        "allow_action": "Apply",
        "ban_action": "Block",
        "zero_in_window": "0 in window",
        "help_title": "### Anima LoRA Stage Scheduler Guide",
        "current_template": "Current template",
        "current_shift": "Current Shift",
        "template_parts": "Template parts:",
        "intro": "Schedule when Anima LoRAs affect sampling: use composition, character, style, or custom timing windows, with separate base and Hires. fix controls.",
        "template_name_required": "Template name is required.",
        "builtin_template_locked": "Built-in templates cannot be overwritten. Choose another name.",
        "template_saved": "Saved template: {name}",
        "preset_required": "Select at least one base preset.",
        "unknown_preset": "Unknown base preset: {preset}",
        "combo_conflict": "Combo conflict: {stage} has both Apply and Block selected, so it cannot be saved.",
        "builtin_preset_locked": "Built-in base presets cannot be overwritten. Choose another name.",
        "combo_saved": "Saved combo template: {name} = {presets}\n\n{preview}",
        "no_template_selected": "No template selected.",
        "builtin_template_rename_locked": "Built-in templates cannot be renamed.",
        "new_name_required": "New name is required.",
        "builtin_name_forbidden": "Cannot rename to a built-in template name.",
        "same_name": "New name is the same as the old name.",
        "template_missing": "Template to rename was not found.",
        "target_name_exists": "Target name already exists.",
        "template_renamed": "Renamed template: {old_name} -> {new_name}",
        "builtin_template_delete_locked": "Built-in templates cannot be deleted.",
        "template_deleted": "Deleted template: {name}",
        "help_line_templates": "- Templates are built from base presets. Apply means the LoRA is active only in that stage; Block forces it to 0 in that stage.",
        "help_line_shift": "- When auto timing from Shift is enabled, every base preset moves its start, end, and peak ratios from the current Shift value.",
        "help_line_combo": "- Combo templates can mix stages, but the same stage cannot be both Apply and Block.",
        "help_line_ratios": "- Start/end are sampling progress ratios from 0 to 1; peak is the strongest point of the curve; stage strength multiplies the final LoRA strength.",
        "help_part_line": "- `{preset}`: {stage} {action}, auto window {start} - {end}, peak {peak}, strength {strength}",
    },
    "ko": {
        "settings_label": "Anima LoRA 단계 스케줄러 UI 언어",
        "title": "Anima LoRA Stage Scheduler",
        "enable": "단계 스케줄링 사용",
        "base_panel": "기본 패스",
        "hires_panel": "Hires. fix 단계",
        "hires_lora_panel": "Hires. fix LoRA 단계",
        "target_scope": "대상 범위",
        "panel_weight": "패널 가중치, 0 = 프롬프트 / 레이어 가중치 플러그인 사용",
        "target_lora": "대상 LoRA",
        "target_lora_placeholder": "대상 범위가 대상 목록일 때만 입력; 여러 이름은 쉼표나 줄바꿈으로 구분",
        "template": "템플릿",
        "copy": "복사",
        "builder": "프리셋 조합",
        "auto_timing": "Shift 기준 자동 타이밍",
        "single_lora_template": "LoRA별 템플릿",
        "single_lora_template_placeholder": "한 줄에 하나씩: LoRA 이름=템플릿 이름\n예: <lora:name:0.8>=character-feature-stage\n비워 둔 LoRA는 위 템플릿을 사용",
        "start": "시작 비율",
        "end": "종료 비율",
        "peak": "피크 비율",
        "strength": "단계 강도 배율",
        "curve": "강도 곡선",
        "hr_independent": "Hires. fix에서 독립 패널 사용; 끄면 기본 설정을 상속하되 Hires Shift로 타이밍 계산",
        "hr_disable": "Hires. fix 중 LoRA 비활성화",
        "hr_disable_tags": "비활성화할 전체 LoRA 태그",
        "template_manager": "템플릿 관리",
        "existing_template": "기존 템플릿",
        "rename_to": "새 이름",
        "rename_template": "템플릿 이름 변경",
        "delete_template": "템플릿 삭제",
        "new_template_name": "새 템플릿 이름",
        "save_auto_template": "자동 타이밍 템플릿으로 저장",
        "save_current_base": "현재 기본 패널을 템플릿으로 저장",
        "template_help": "### 템플릿 안내",
        "close": "닫기",
        "combo_title": "### 프리셋 조합",
        "template_name": "템플릿 이름",
        "base_preset_combo": "기본 프리셋 조합",
        "preview_shift": "미리보기 Shift",
        "save_combo": "조합 템플릿 저장",
        "combo_current": "현재 조합: ",
        "intervention_preview": "타이밍 미리보기",
        "table_preset": "기본 프리셋",
        "table_action": "동작",
        "table_start": "시작",
        "table_end": "종료",
        "table_peak": "피크",
        "table_strength": "강도",
        "table_curve": "곡선",
        "allow_action": "적용",
        "ban_action": "차단",
        "zero_in_window": "창 안에서 0",
        "help_title": "### Anima LoRA 단계 스케줄러 안내",
        "current_template": "현재 템플릿",
        "current_shift": "현재 Shift",
        "template_parts": "템플릿 구성:",
        "intro": "Anima LoRA가 샘플링에 영향을 주는 시점을 조절합니다. 구도, 캐릭터, 스타일 또는 사용자 지정 타이밍 창을 사용할 수 있고 기본 패스와 Hires. fix를 따로 제어할 수 있습니다.",
        "template_name_required": "템플릿 이름이 필요합니다.",
        "builtin_template_locked": "내장 템플릿은 덮어쓸 수 없습니다. 다른 이름을 선택하세요.",
        "template_saved": "템플릿 저장됨: {name}",
        "preset_required": "기본 프리셋을 하나 이상 선택하세요.",
        "unknown_preset": "알 수 없는 기본 프리셋: {preset}",
        "combo_conflict": "조합 충돌: {stage}에 적용과 차단이 동시에 선택되어 저장할 수 없습니다.",
        "builtin_preset_locked": "내장 기본 프리셋은 덮어쓸 수 없습니다. 다른 이름을 선택하세요.",
        "combo_saved": "조합 템플릿 저장됨: {name} = {presets}\n\n{preview}",
        "no_template_selected": "선택된 템플릿이 없습니다.",
        "builtin_template_rename_locked": "내장 템플릿은 이름을 바꿀 수 없습니다.",
        "new_name_required": "새 이름이 필요합니다.",
        "builtin_name_forbidden": "내장 템플릿 이름으로 바꿀 수 없습니다.",
        "same_name": "새 이름이 기존 이름과 같습니다.",
        "template_missing": "이름을 바꿀 템플릿을 찾을 수 없습니다.",
        "target_name_exists": "대상 이름이 이미 있습니다.",
        "template_renamed": "템플릿 이름 변경됨: {old_name} -> {new_name}",
        "builtin_template_delete_locked": "내장 템플릿은 삭제할 수 없습니다.",
        "template_deleted": "템플릿 삭제됨: {name}",
        "help_line_templates": "- 템플릿은 기본 프리셋 조합으로 구성됩니다. 적용은 해당 단계에서만 LoRA를 켜고, 차단은 해당 단계에서 LoRA를 0으로 만듭니다.",
        "help_line_shift": "- Shift 기준 자동 타이밍을 켜면 각 기본 프리셋의 시작, 종료, 피크 비율이 현재 Shift 값에 맞게 이동합니다.",
        "help_line_combo": "- 조합 템플릿은 여러 단계를 섞을 수 있지만 같은 단계에 적용과 차단을 동시에 둘 수 없습니다.",
        "help_line_ratios": "- 시작/종료는 0에서 1 사이의 샘플링 진행 비율이고, 피크는 곡선이 가장 강한 지점이며, 단계 강도는 최종 LoRA 강도에 곱해집니다.",
        "help_part_line": "- `{preset}`: {stage} {action}, 자동 창 {start} - {end}, 피크 {peak}, 강도 {strength}",
    },
}


def _language():
    value = str(getattr(shared.opts, LANGUAGE_OPTION, "en") or "en").strip().lower()
    if value == LEGACY_LANGUAGE_VALUE:
        return "ko"
    return value if value in LANGUAGE_CHOICES else "en"


def _t(key):
    return LANG.get(_language(), LANG["en"]).get(key, key)


def _intro_block(elem_id):
    gr.Markdown(value=_t("intro"), elem_id=elem_id("intro"))


def _labels(mapping):
    return mapping.get(_language(), mapping["en"])


def _normalize_with_alias(value, aliases, default):
    text = str(value or "").strip()
    if text in aliases:
        return aliases[text]
    lowered = text.lower()
    return aliases.get(lowered, default)


def _contains_han(text) -> bool:
    return HAN_RE.search(str(text or "")) is not None


def _target_mode_choices():
    labels = _labels(TARGET_MODE_LABELS)
    return [labels[item] for item in TARGET_MODE_CHOICES]


def _display_target_mode(value):
    canonical = _normalize_target_mode(value)
    return _labels(TARGET_MODE_LABELS).get(canonical, canonical)


def _normalize_target_mode(value):
    return _normalize_with_alias(value, TARGET_MODE_ALIASES, MODE_AUTO_ANIMA)


def _disable_choices():
    labels = _labels(DISABLE_LABELS)
    return [labels[item] for item in DISABLE_CHOICES]


def _display_disable_mode(value):
    canonical = _normalize_disable_mode(value)
    return _labels(DISABLE_LABELS).get(canonical, canonical)


def _normalize_disable_mode(value):
    return _normalize_with_alias(value, DISABLE_ALIASES, DISABLE_NONE)


def _curve_choices():
    labels = _labels(CURVE_LABELS)
    return [labels[item] for item in CURVE_CHOICES]


def _display_curve(value):
    canonical = _normalize_curve(value)
    return _labels(CURVE_LABELS).get(canonical, canonical)


def _normalize_curve(value):
    return _normalize_with_alias(value, CURVE_ALIASES, CURVE_SMOOTH)


def _display_stage(value):
    canonical = _normalize_stage(value)
    return _labels(STAGE_LABELS).get(canonical, canonical)


def _normalize_stage(value, fallback=None):
    default = fallback or STAGE_CHARACTER
    return _normalize_with_alias(value, STAGE_ALIASES, default)


def _display_preset(value):
    canonical = _normalize_preset_name(value)
    return _labels(PRESET_LABELS).get(canonical, canonical)


def _normalize_preset_name(value):
    return _normalize_with_alias(value, PRESET_ALIASES, str(value or "").strip())


def _display_template_name(value):
    canonical = _normalize_template_name(value)
    return _labels(TEMPLATE_LABELS).get(canonical, canonical)


def _normalize_template_name(value):
    return _normalize_with_alias(value, TEMPLATE_ALIASES, str(value or "").strip())


def _builder_preset_choices():
    return [_display_preset(item) for item in TEMPLATE_PRESET_CHOICES]


def _register_ui_settings():
    categories.register_category("extensions", "Extensions")
    info = shared.OptionInfo(
        "en",
        _t("settings_label"),
        gr.Radio,
        {"choices": LANGUAGE_CHOICES},
        section=("anima-lora-stage-scheduler", "Anima LoRA Stage Scheduler"),
        category_id="extensions",
    ).needs_reload_ui()
    if LANGUAGE_OPTION in shared.opts.data_labels:
        shared.opts.data_labels[LANGUAGE_OPTION] = info
        if getattr(shared.opts, LANGUAGE_OPTION, None) == LEGACY_LANGUAGE_VALUE:
            setattr(shared.opts, LANGUAGE_OPTION, "ko")
        return
    shared.opts.add_option(LANGUAGE_OPTION, info)


script_callbacks.on_ui_settings(_register_ui_settings)

EXTENSION_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = EXTENSION_DIR / "templates.json"

LORA_TAG_RE = re.compile(r"<lora:([^:>]+)(?::([^>]*))?>")
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
ANIMA_BLOCK_RE = re.compile(r"(?:^|\.)(?:diffusion_model\.)?(?:net\.)?blocks\.(\d+)\.")
QWEN_LAYER_RE = re.compile(r"(?:^|\.)(?:text_encoders\.)?qwen3_06b\.model\.layers\.(\d+)\.")
GENERIC_QWEN_LAYER_RE = re.compile(r"(?:^|\.)(?:text_encoders\.)?qwen3_06b\.(?:model\.)?layers\.(\d+)\.")
QWEN_ADAPTER_BLOCK_RE = re.compile(r"(?:^|\.)(?:text_encoders\.)?qwen3_06b\.llm_adapter\.blocks\.(\d+)\.")
LEGACY_QWEN_ADAPTER_BLOCK_RE = re.compile(r"(?:^|\.)(?:diffusion_model\.)?llm_adapter\.blocks\.(\d+)\.")

MODE_AUTO_ANIMA = "auto-anima"
MODE_PROMPT_ALL = "prompt-all"
MODE_TARGETS = "targets"
TARGET_MODE_CHOICES = [MODE_AUTO_ANIMA, MODE_PROMPT_ALL, MODE_TARGETS]
TARGET_MODE_LABELS = {
    "en": {
        MODE_AUTO_ANIMA: "Auto-detect Anima LoRA",
        MODE_PROMPT_ALL: "All LoRAs in prompt",
        MODE_TARGETS: "Target list only",
    },
    "ko": {
        MODE_AUTO_ANIMA: "Anima LoRA 자동 감지",
        MODE_PROMPT_ALL: "프롬프트의 모든 LoRA",
        MODE_TARGETS: "대상 목록만",
    },
}
TARGET_MODE_ALIASES = {item: item for item in TARGET_MODE_CHOICES}

STAGE_COMPOSITION = "composition"
STAGE_CHARACTER = "character"
STAGE_STYLE = "style"
STAGE_CHOICES = [STAGE_COMPOSITION, STAGE_CHARACTER, STAGE_STYLE]
STAGE_LABELS = {
    "en": {
        STAGE_COMPOSITION: "Composition stage",
        STAGE_CHARACTER: "Character-feature stage",
        STAGE_STYLE: "Style stage",
    },
    "ko": {
        STAGE_COMPOSITION: "구도 단계",
        STAGE_CHARACTER: "캐릭터 특징 단계",
        STAGE_STYLE: "스타일 단계",
    },
}
STAGE_ALIASES = {item: item for item in STAGE_CHOICES}

PART_ALLOW = "allow"
PART_BAN = "ban"

PRESET_STYLE_ALLOW = "style-stage"
PRESET_COMPOSITION_ALLOW = "composition-stage"
PRESET_CHARACTER_ALLOW = "character-feature-stage"
PRESET_STYLE_BAN = "block-style-stage"
PRESET_COMPOSITION_BAN = "block-composition-stage"
PRESET_CHARACTER_BAN = "block-character-feature-stage"
TEMPLATE_PRESET_CHOICES = [
    PRESET_STYLE_ALLOW,
    PRESET_COMPOSITION_ALLOW,
    PRESET_CHARACTER_ALLOW,
    PRESET_STYLE_BAN,
    PRESET_COMPOSITION_BAN,
    PRESET_CHARACTER_BAN,
]
PRESET_LABELS = {
    "en": {
        PRESET_STYLE_ALLOW: "Style stage only",
        PRESET_COMPOSITION_ALLOW: "Composition stage only",
        PRESET_CHARACTER_ALLOW: "Character-feature stage only",
        PRESET_STYLE_BAN: "Block style stage",
        PRESET_COMPOSITION_BAN: "Block composition stage",
        PRESET_CHARACTER_BAN: "Block character-feature stage",
    },
    "ko": {
        PRESET_STYLE_ALLOW: "스타일 단계만 적용",
        PRESET_COMPOSITION_ALLOW: "구도 단계만 적용",
        PRESET_CHARACTER_ALLOW: "캐릭터 특징 단계만 적용",
        PRESET_STYLE_BAN: "스타일 단계 차단",
        PRESET_COMPOSITION_BAN: "구도 단계 차단",
        PRESET_CHARACTER_BAN: "캐릭터 특징 단계 차단",
    },
}
PRESET_ALIASES = {item: item for item in TEMPLATE_PRESET_CHOICES}

CURVE_HOLD = "hold"
CURVE_SMOOTH = "smooth"
CURVE_TRIANGLE = "triangle"
CURVE_FRONT = "front-heavy"
CURVE_BACK = "back-heavy"
CURVE_CHOICES = [CURVE_SMOOTH, CURVE_HOLD, CURVE_TRIANGLE, CURVE_FRONT, CURVE_BACK]
CURVE_LABELS = {
    "en": {
        CURVE_SMOOTH: "Smooth fade",
        CURVE_HOLD: "Hold",
        CURVE_TRIANGLE: "Linear triangle",
        CURVE_FRONT: "Front-heavy",
        CURVE_BACK: "Back-heavy",
    },
    "ko": {
        CURVE_SMOOTH: "부드러운 페이드",
        CURVE_HOLD: "유지",
        CURVE_TRIANGLE: "선형 삼각",
        CURVE_FRONT: "앞쪽 강함",
        CURVE_BACK: "뒤쪽 강함",
    },
}
CURVE_ALIASES = {item: item for item in CURVE_CHOICES}

DISABLE_NONE = "none"
DISABLE_ALL = "all"
DISABLE_SELECTED = "selected"
DISABLE_CHOICES = [DISABLE_NONE, DISABLE_ALL, DISABLE_SELECTED]
DISABLE_LABELS = {
    "en": {
        DISABLE_NONE: "Do not disable",
        DISABLE_ALL: "Disable all LoRAs",
        DISABLE_SELECTED: "Disable listed full tags",
    },
    "ko": {
        DISABLE_NONE: "비활성화하지 않음",
        DISABLE_ALL: "모든 LoRA 비활성화",
        DISABLE_SELECTED: "나열한 전체 태그 비활성화",
    },
}
DISABLE_ALIASES = {item: item for item in DISABLE_CHOICES}

STAGE_DEFAULT_CURVES = {
    STAGE_COMPOSITION: CURVE_FRONT,
    STAGE_CHARACTER: CURVE_SMOOTH,
    STAGE_STYLE: CURVE_SMOOTH,
}

PRESET_PARTS = {
    PRESET_STYLE_ALLOW: {"stage": STAGE_STYLE, "mode": PART_ALLOW},
    PRESET_COMPOSITION_ALLOW: {"stage": STAGE_COMPOSITION, "mode": PART_ALLOW},
    PRESET_CHARACTER_ALLOW: {"stage": STAGE_CHARACTER, "mode": PART_ALLOW},
    PRESET_STYLE_BAN: {"stage": STAGE_STYLE, "mode": PART_BAN},
    PRESET_COMPOSITION_BAN: {"stage": STAGE_COMPOSITION, "mode": PART_BAN},
    PRESET_CHARACTER_BAN: {"stage": STAGE_CHARACTER, "mode": PART_BAN},
}

BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT = "anti-style-overfit"
TEMPLATE_LABELS = {
    "en": {
        PRESET_STYLE_ALLOW: "Style stage only",
        PRESET_COMPOSITION_ALLOW: "Composition stage only",
        PRESET_CHARACTER_ALLOW: "Character-feature stage only",
        PRESET_STYLE_BAN: "Block style stage",
        PRESET_COMPOSITION_BAN: "Block composition stage",
        PRESET_CHARACTER_BAN: "Block character-feature stage",
        BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT: "Anti-style overfit",
    },
    "ko": {
        PRESET_STYLE_ALLOW: "스타일 단계만 적용",
        PRESET_COMPOSITION_ALLOW: "구도 단계만 적용",
        PRESET_CHARACTER_ALLOW: "캐릭터 특징 단계만 적용",
        PRESET_STYLE_BAN: "스타일 단계 차단",
        PRESET_COMPOSITION_BAN: "구도 단계 차단",
        PRESET_CHARACTER_BAN: "캐릭터 특징 단계 차단",
        BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT: "스타일 과적합 방지",
    },
}
TEMPLATE_ALIASES = {
    PRESET_STYLE_ALLOW: PRESET_STYLE_ALLOW,
    PRESET_COMPOSITION_ALLOW: PRESET_COMPOSITION_ALLOW,
    PRESET_CHARACTER_ALLOW: PRESET_CHARACTER_ALLOW,
    PRESET_STYLE_BAN: PRESET_STYLE_BAN,
    PRESET_COMPOSITION_BAN: PRESET_COMPOSITION_BAN,
    PRESET_CHARACTER_BAN: PRESET_CHARACTER_BAN,
    BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT: BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT,
}

BUILTIN_TEMPLATES = {
    PRESET_STYLE_ALLOW: {
        "stage": STAGE_STYLE,
        "parts": [PRESET_PARTS[PRESET_STYLE_ALLOW]],
        "auto": True,
        "start": 0.62,
        "end": 1.0,
        "peak": 0.86,
        "strength": 1.0,
        "curve": CURVE_SMOOTH,
    },
    PRESET_COMPOSITION_ALLOW: {
        "stage": STAGE_COMPOSITION,
        "parts": [PRESET_PARTS[PRESET_COMPOSITION_ALLOW]],
        "auto": True,
        "start": 0.0,
        "end": 0.32,
        "peak": 0.08,
        "strength": 1.0,
        "curve": CURVE_FRONT,
    },
    PRESET_CHARACTER_ALLOW: {
        "stage": STAGE_CHARACTER,
        "parts": [PRESET_PARTS[PRESET_CHARACTER_ALLOW]],
        "auto": True,
        "start": 0.20,
        "end": 0.74,
        "peak": 0.48,
        "strength": 1.0,
        "curve": CURVE_SMOOTH,
    },
    PRESET_STYLE_BAN: {
        "stage": STAGE_STYLE,
        "parts": [PRESET_PARTS[PRESET_STYLE_BAN]],
        "auto": True,
        "start": 0.62,
        "end": 1.0,
        "peak": 0.86,
        "strength": 1.0,
        "curve": CURVE_SMOOTH,
    },
    PRESET_COMPOSITION_BAN: {
        "stage": STAGE_COMPOSITION,
        "parts": [PRESET_PARTS[PRESET_COMPOSITION_BAN]],
        "auto": True,
        "start": 0.0,
        "end": 0.32,
        "peak": 0.08,
        "strength": 1.0,
        "curve": CURVE_FRONT,
    },
    PRESET_CHARACTER_BAN: {
        "stage": STAGE_CHARACTER,
        "parts": [PRESET_PARTS[PRESET_CHARACTER_BAN]],
        "auto": True,
        "start": 0.20,
        "end": 0.74,
        "peak": 0.48,
        "strength": 1.0,
        "curve": CURVE_SMOOTH,
    },
}

for labels in (TARGET_MODE_LABELS, STAGE_LABELS, PRESET_LABELS, CURVE_LABELS, DISABLE_LABELS, TEMPLATE_LABELS):
    for values in labels.values():
        for canonical, label in values.items():
            target = canonical
            if labels is TARGET_MODE_LABELS:
                TARGET_MODE_ALIASES[label] = canonical
                TARGET_MODE_ALIASES[label.lower()] = canonical
            elif labels is STAGE_LABELS:
                STAGE_ALIASES[label] = canonical
                STAGE_ALIASES[label.lower()] = canonical
            elif labels is PRESET_LABELS:
                PRESET_ALIASES[label] = canonical
                PRESET_ALIASES[label.lower()] = canonical
            elif labels is CURVE_LABELS:
                CURVE_ALIASES[label] = canonical
                CURVE_ALIASES[label.lower()] = canonical
            elif labels is DISABLE_LABELS:
                DISABLE_ALIASES[label] = canonical
                DISABLE_ALIASES[label.lower()] = canonical
            elif labels is TEMPLATE_LABELS:
                TEMPLATE_ALIASES[label] = target
                TEMPLATE_ALIASES[label.lower()] = target

_LEGACY_TARGET_MODE_ALIASES = {
    "\u81ea\u52a8\u8bc6\u522b Anima LoRA": MODE_AUTO_ANIMA,
    "\u63d0\u793a\u8bcd\u4e2d\u7684\u5168\u90e8 LoRA": MODE_PROMPT_ALL,
    "\u4ec5\u76ee\u6807\u5217\u8868": MODE_TARGETS,
}
_LEGACY_STAGE_ALIASES = {
    "\u6784\u56fe\u9636\u6bb5": STAGE_COMPOSITION,
    "\u4eba\u7269\u7279\u5f81\u9636\u6bb5": STAGE_CHARACTER,
    "\u753b\u98ce\u9636\u6bb5": STAGE_STYLE,
}
_LEGACY_PRESET_ALIASES = {
    "\u4ec5\u753b\u98ce\u9636\u6bb5\u4ecb\u5165": PRESET_STYLE_ALLOW,
    "\u4ec5\u6784\u56fe\u9636\u6bb5\u4ecb\u5165": PRESET_COMPOSITION_ALLOW,
    "\u4ec5\u4eba\u7269\u7279\u5f81\u9636\u6bb5\u4ecb\u5165": PRESET_CHARACTER_ALLOW,
    "\u4ec5\u7981\u6b62\u753b\u98ce\u9636\u6bb5\u4ecb\u5165": PRESET_STYLE_BAN,
    "\u4ec5\u7981\u6b62\u6784\u56fe\u9636\u6bb5": PRESET_COMPOSITION_BAN,
    "\u4ec5\u7981\u6b62\u4eba\u7269\u7279\u5f81\u9636\u6bb5": PRESET_CHARACTER_BAN,
    "\u5355\u753b\u98ce\u9636\u6bb5\u4ecb\u5165": PRESET_STYLE_ALLOW,
    "\u5355\u6784\u56fe\u9636\u6bb5\u4ecb\u5165": PRESET_COMPOSITION_ALLOW,
    "\u5355\u4eba\u7269\u7279\u5f81\u9636\u6bb5\u4ecb\u5165": PRESET_CHARACTER_ALLOW,
    "\u5355\u7981\u6b62\u753b\u98ce\u9636\u6bb5\u4ecb\u5165": PRESET_STYLE_BAN,
    "\u5355\u7981\u6b62\u6784\u56fe\u9636\u6bb5": PRESET_COMPOSITION_BAN,
    "\u5355\u7981\u6b62\u4eba\u7269\u7279\u5f81\u9636\u6bb5": PRESET_CHARACTER_BAN,
}
_LEGACY_CURVE_ALIASES = {
    "\u4fdd\u6301": CURVE_HOLD,
    "\u5e73\u6ed1\u6de1\u5165\u6de1\u51fa": CURVE_SMOOTH,
    "\u7ebf\u6027\u4e09\u89d2": CURVE_TRIANGLE,
    "\u524d\u5f3a\u540e\u5f31": CURVE_FRONT,
    "\u540e\u5f3a\u524d\u5f31": CURVE_BACK,
}
_LEGACY_DISABLE_ALIASES = {
    "\u4e0d\u7981\u7528": DISABLE_NONE,
    "\u7981\u7528\u5168\u90e8 LoRA": DISABLE_ALL,
    "\u7981\u7528\u6307\u5b9a\u5b8c\u6574\u6807\u7b7e": DISABLE_SELECTED,
}
_LEGACY_TEMPLATE_ALIASES = {
    **_LEGACY_PRESET_ALIASES,
    "\u9632\u753b\u98ce\u8fc7\u62df\u5408": BUILTIN_TEMPLATE_ANTI_STYLE_OVERFIT,
}
for alias_map, target_map in [
    (_LEGACY_TARGET_MODE_ALIASES, TARGET_MODE_ALIASES),
    (_LEGACY_STAGE_ALIASES, STAGE_ALIASES),
    (_LEGACY_PRESET_ALIASES, PRESET_ALIASES),
    (_LEGACY_CURVE_ALIASES, CURVE_ALIASES),
    (_LEGACY_DISABLE_ALIASES, DISABLE_ALIASES),
    (_LEGACY_TEMPLATE_ALIASES, TEMPLATE_ALIASES),
]:
    for legacy, canonical in alias_map.items():
        target_map.setdefault(legacy, canonical)
        target_map.setdefault(legacy.lower(), canonical)

_ACTIVE_STATE = None
_ORIGINAL_ADD_PATCHES = None
_ORIGINAL_EXTRA_NETWORKS_ACTIVATE = None
_CFG_CALLBACK_REGISTERED = False


def _clamp(value, low, high):
    return max(low, min(high, value))


def _to_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback


def _is_plain_number(text) -> bool:
    return re.fullmatch(r"\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*", str(text or "")) is not None


def _format_float(value):
    text = f"{_to_float(value):.8f}".rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"


def _normalize_name(name: str) -> str:
    return str(name or "").strip().lower()


def _parse_targets(text) -> set[str]:
    normalized = str(text or "").replace("，", ",").replace("；", ";")
    parts = re.split(r"[,;\n]+", normalized)
    targets = set()
    for part in parts:
        name = _normalize_name(part)
        if not name:
            continue
        targets.add(name)
        path = Path(name)
        targets.add(path.name.lower())
        targets.add(path.stem.lower())
    return {x for x in targets if x}


def _compact_text(text) -> str:
    return " ".join(str(text or "").replace("\r", "\n").split())


def _model_key(key) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, tuple) and key:
        return str(key[0])
    return str(key or "")


@dataclass
class LayerWeights:
    default: float = 1.0
    values: dict[int, float] = field(default_factory=dict)

    def factor(self, index: int) -> float:
        return self.values.get(index, self.default)


def _module_key(name: str) -> str:
    key = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "self": "self_attn",
        "selfattn": "self_attn",
        "self_attention": "self_attn",
        "cross": "cross_attn",
        "crossattn": "cross_attn",
        "cross_attention": "cross_attn",
        "ada": "adaln",
        "adaln_modulation": "adaln",
        "modulation": "adaln",
        "norms": "norm",
        "layernorm": "norm",
        "feedforward": "mlp",
        "ffn": "mlp",
    }
    return aliases.get(key, key)


def _looks_like_layer_weights(text) -> bool:
    value = str(text or "").strip()
    value = re.sub(r"\bblock_lrs?\s*=", "", value, flags=re.IGNORECASE)
    if not value or _is_plain_number(value):
        return False

    tokens = [t for t in re.split(r"[\s,，;；]+", value) if t]
    numeric_count = 0
    for token in tokens:
        if "=" in token:
            left, _ = token.split("=", 1)
            left = left.strip().lower()
            if left in {"*", "all", "default"} or left.isdigit() or re.fullmatch(r"\d+\s*-\s*\d+", left):
                return True
            continue
        if _is_plain_number(token):
            numeric_count += 1

    return numeric_count >= 2


def _parse_layer_weights(text) -> LayerWeights:
    source = str(text or "").strip().replace("，", ",").replace("；", ";").replace("：", "=")
    source = re.sub(r"\bblock_lrs?\s*=", "", source, flags=re.IGNORECASE)
    values = {}
    default = 1.0
    bare_values = []

    for token in [t for t in re.split(r"[\s,;]+", source) if t]:
        if "=" not in token:
            try:
                bare_values.append(float(token))
            except Exception:
                logger.warning("Ignored invalid Anima stage layer token: %s", token)
            continue

        left, right = token.split("=", 1)
        left = left.strip().lower()
        value = _to_float(right, 1.0)

        if left in {"*", "all", "default"}:
            default = value
            continue

        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", left)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start > end:
                start, end = end, start
            for index in range(start, end + 1):
                values[index] = value
            continue

        if left.isdigit():
            values[int(left)] = value
        else:
            logger.warning("Ignored invalid Anima stage layer selector: %s", left)

    if bare_values and not values:
        values.update({i: v for i, v in enumerate(bare_values)})

    return LayerWeights(default=default, values=values)


def _parse_module_weights(text) -> dict[str, float]:
    weights = {}
    source = str(text or "").replace("，", ",").replace("；", ";").replace("：", "=")
    for token in [t for t in re.split(r"[\n,;]+", source) if t.strip()]:
        if "=" not in token:
            continue
        left, right = token.split("=", 1)
        weights[_module_key(left)] = _to_float(right, 1.0)
    return weights


def _split_panel_weight_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    bare_parts = []

    for part in [p.strip() for p in re.split(r"[;；]+", str(text or "")) if p.strip()]:
        if "=" in part or "：" in part:
            if "=" in part:
                left, right = part.split("=", 1)
            else:
                left, right = part.split("：", 1)
            key = left.strip().lower()
            if key in {"blocks", "block", "layers", "layer", "block_lrs", "block_lr"}:
                sections["blocks"] = part.strip() if key in {"block_lrs", "block_lr"} else right.strip()
                continue
            if key in {"modules", "module", "mods", "mod"}:
                sections["modules"] = right.strip()
                continue
            if key in {"qwen", "text", "text_encoder", "text_layers", "te"}:
                sections["qwen"] = right.strip()
                continue
        bare_parts.append(part)

    if bare_parts:
        if "blocks" in sections:
            sections["blocks"] = ";".join([sections["blocks"], *bare_parts])
        else:
            sections["blocks"] = ";".join(bare_parts)

    return sections


def _block_index_from_key(key: str) -> int | None:
    key_text = str(key or "")
    match = ANIMA_BLOCK_RE.search(key_text)
    if match:
        return int(match.group(1))

    normalized = key_text.lower().replace(".", "_")
    match = re.search(r"(?:^|_)blocks_(\d+)(?:_|$)", normalized)
    if not match:
        return None
    return int(match.group(1))


def _module_name_from_block_tail(module: str) -> str | None:
    if module.startswith("adaln_modulation"):
        return "adaln"
    if module.startswith("norm"):
        return "norm"
    if module.startswith("self_attn"):
        return "self_attn"
    if module.startswith("cross_attn"):
        return "cross_attn"
    if module.startswith("mlp"):
        return "mlp"
    return None


def _module_from_key(key: str) -> str | None:
    key_text = str(key or "")
    marker = re.search(r"blocks\.\d+\.([^.]+)", key_text)
    if marker:
        module = _module_name_from_block_tail(marker.group(1))
        return module or _module_key(marker.group(1))

    normalized = key_text.lower().replace(".", "_")
    marker = re.search(r"(?:^|_)blocks_\d+_(.+)", normalized)
    if not marker:
        return None

    return _module_name_from_block_tail(marker.group(1))


def _module_factor(key: str, module_weights: dict[str, float]) -> float:
    module = _module_from_key(key)
    if not module:
        return 1.0
    return module_weights.get(module, 1.0)


def _qwen_layer_index(key: str) -> int | None:
    key_text = str(key or "")
    match = QWEN_LAYER_RE.search(key_text) or GENERIC_QWEN_LAYER_RE.search(key_text) or QWEN_ADAPTER_BLOCK_RE.search(key_text) or LEGACY_QWEN_ADAPTER_BLOCK_RE.search(key_text)
    if match:
        return int(match.group(1))

    normalized = key_text.lower().replace(".", "_")
    match = (
        re.search(r"qwen3_06b_(?:model_)?layers_(\d+)", normalized)
        or re.search(r"qwen3_06b_llm_adapter_blocks_(\d+)", normalized)
        or re.search(r"(?:^|_)llm_adapter_blocks_(\d+)", normalized)
    )
    if not match:
        return None
    return int(match.group(1))


@dataclass
class PanelWeightSpec:
    raw: str = "0"
    numeric: float | None = None
    block_weights: LayerWeights = field(default_factory=LayerWeights)
    module_weights: dict[str, float] = field(default_factory=dict)
    qwen_weights: LayerWeights = field(default_factory=LayerWeights)
    has_block: bool = False
    has_module: bool = False
    has_qwen: bool = False

    @property
    def active(self) -> bool:
        return self.numeric is not None or self.has_block or self.has_module or self.has_qwen

    def prompt_multiplier(self) -> float:
        return self.numeric if self.numeric is not None else 1.0

    def strength_for_key(self, key, fallback):
        if self.numeric is not None:
            return self.numeric

        model_key = _model_key(key)
        qwen_layer = _qwen_layer_index(model_key)
        if qwen_layer is not None:
            return self.qwen_weights.factor(qwen_layer) if self.has_qwen else 1.0

        block_index = _block_index_from_key(model_key)
        if block_index is not None:
            factor = self.block_weights.factor(block_index) if self.has_block else 1.0
            if self.has_module:
                factor *= _module_factor(model_key, self.module_weights)
            return factor

        return 1.0


def _parse_panel_weight(text) -> PanelWeightSpec:
    raw = str(text or "").strip()
    spec = PanelWeightSpec(raw=raw or "0")
    if not raw:
        return spec

    if _is_plain_number(raw):
        value = _to_float(raw, 0.0)
        if abs(value) > 1e-12:
            spec.numeric = value
        return spec

    sections = _split_panel_weight_sections(raw)
    block_text = sections.get("blocks", "")
    module_text = sections.get("modules", "")
    qwen_text = sections.get("qwen", "")

    if block_text and _looks_like_layer_weights(block_text):
        spec.block_weights = _parse_layer_weights(block_text)
        spec.has_block = True
    if module_text:
        spec.module_weights = _parse_module_weights(module_text)
        spec.has_module = bool(spec.module_weights)
    if qwen_text and _looks_like_layer_weights(qwen_text):
        spec.qwen_weights = _parse_layer_weights(qwen_text)
        spec.has_qwen = True

    if not spec.active:
        logger.warning("Ignored invalid Anima stage panel weight syntax: %s", raw)
    return spec


def _parse_disable_tags(text) -> list[str]:
    tags = []
    for line in str(text or "").replace("\r", "\n").split("\n"):
        tag = line.strip()
        if tag:
            tags.append(tag)
    return tags


def _selector_names(selector: str) -> set[str]:
    value = str(selector or "").strip()
    if not value:
        return set()

    match = LORA_TAG_RE.fullmatch(value)
    if match:
        value = match.group(1)

    return _parse_targets(value)


def _parse_lora_template_overrides(text) -> dict[str, str]:
    templates = set(_template_names())
    overrides: dict[str, str] = {}

    for raw_line in str(text or "").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "->" in line:
            left, right = line.rsplit("->", 1)
        elif "=>" in line:
            left, right = line.rsplit("=>", 1)
        elif "=" in line:
            left, right = line.rsplit("=", 1)
        elif "＝" in line:
            left, right = line.rsplit("＝", 1)
        else:
            logger.warning("Ignored invalid Anima per-LoRA template line: %s", line)
            continue

        template_name = _normalize_template_name(right.strip())
        if template_name not in templates:
            logger.warning("Ignored unknown Anima per-LoRA template: %s", template_name)
            continue

        names = _selector_names(left)
        if not names:
            logger.warning("Ignored empty Anima per-LoRA template selector: %s", line)
            continue

        for name in names:
            overrides[name] = template_name

    return overrides


def _load_custom_templates() -> dict:
    if not TEMPLATE_FILE.exists():
        return {}
    try:
        with TEMPLATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        migrated, changed = _migrate_template_data(data)
        if changed:
            _save_custom_templates(migrated)
        return migrated
    except Exception:
        logger.exception("Failed to read Anima LoRA stage templates")
        return {}


def _save_custom_templates(data: dict):
    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TEMPLATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _template_names() -> list[str]:
    names = list(BUILTIN_TEMPLATES.keys())
    for name in _load_custom_templates():
        logical_name = _normalize_template_name(name)
        if logical_name not in names:
            names.append(logical_name)
    return names


def _template_choice_names() -> list[str]:
    return [_display_template_name(name) for name in _template_names()]


def _template_dropdown_update(value=None):
    choices = _template_choice_names()
    logical_value = _normalize_template_name(value)
    names = _template_names()
    if logical_value not in names:
        logical_value = names[0] if names else None
    display_value = _display_template_name(logical_value) if logical_value else None
    return gr.update(choices=choices, value=display_value)


def _template_config(name: str) -> dict:
    name = _normalize_template_name(name)
    if name in BUILTIN_TEMPLATES:
        return dict(BUILTIN_TEMPLATES[name])
    data = _load_custom_templates()
    value = data.get(name, {})
    return dict(value) if isinstance(value, dict) else {}


def _normalize_template_part(part) -> dict | None:
    if isinstance(part, str):
        part = PRESET_PARTS.get(_normalize_preset_name(part))
    if not isinstance(part, dict):
        return None

    stage = _normalize_stage(part.get("stage"), None)
    mode = part.get("mode", PART_ALLOW)
    if stage not in STAGE_CHOICES or mode not in {PART_ALLOW, PART_BAN}:
        return None
    curve = _normalize_curve(part.get("curve") or STAGE_DEFAULT_CURVES.get(stage, CURVE_SMOOTH))

    return {
        "stage": stage,
        "mode": mode,
        "curve": curve if curve in CURVE_CHOICES else STAGE_DEFAULT_CURVES.get(stage, CURVE_SMOOTH),
        "strength": _clamp(_to_float(part.get("strength", 1.0), 1.0), 0.0, 4.0),
    }


def _normalize_template_config(config: dict) -> dict:
    normalized = dict(config)
    stage = _normalize_stage(normalized.get("stage"), STAGE_CHARACTER)
    normalized["stage"] = stage if stage in STAGE_CHOICES else STAGE_CHARACTER
    normalized["curve"] = _normalize_curve(normalized.get("curve") or STAGE_DEFAULT_CURVES.get(normalized["stage"], CURVE_SMOOTH))
    parts = _template_parts(normalized)
    if parts:
        normalized["parts"] = parts
    elif "parts" in normalized:
        normalized.pop("parts", None)
    return normalized


def _migrate_template_data(data: dict) -> tuple[dict, bool]:
    migrated = {}
    changed = False
    custom_index = 1
    for raw_name, raw_config in data.items():
        name = _normalize_template_name(raw_name)
        if _contains_han(name):
            name = ""
        if not name or name in BUILTIN_TEMPLATES:
            while f"custom-template-{custom_index}" in migrated:
                custom_index += 1
            name = f"custom-template-{custom_index}"
            custom_index += 1
            changed = True
        if name != raw_name:
            changed = True
        if name in migrated:
            while f"custom-template-{custom_index}" in migrated:
                custom_index += 1
            name = f"custom-template-{custom_index}"
            custom_index += 1
            changed = True

        config = _normalize_template_config(raw_config) if isinstance(raw_config, dict) else {}
        if config != raw_config:
            changed = True
        migrated[name] = config
    return migrated, changed


def _part_preset_display_name(part: dict) -> str:
    normalized = _normalize_template_part(part)
    if not normalized:
        return ""
    canonical = _part_preset_name(normalized)
    return _display_preset(canonical)


def _template_parts(config: dict) -> list[dict]:
    raw_parts = config.get("parts")
    if isinstance(raw_parts, list):
        parts = [_normalize_template_part(part) for part in raw_parts]
        return [part for part in parts if part is not None]
    return []


def _part_preset_name(part: dict) -> str:
    normalized = _normalize_template_part(part)
    if not normalized:
        return ""
    for name, preset_part in PRESET_PARTS.items():
        if preset_part["stage"] == normalized["stage"] and preset_part["mode"] == normalized["mode"]:
            return name
    return ""


def _stage_from_template_value(value, fallback=STAGE_CHARACTER) -> str:
    stage = _normalize_stage(value, None)
    if stage in STAGE_CHOICES:
        return stage
    part = PRESET_PARTS.get(_normalize_preset_name(value))
    if part:
        return part["stage"]
    return fallback


def _primary_template_part(config: dict, fallback_stage=STAGE_CHARACTER) -> dict:
    parts = _template_parts(config)
    for part in parts:
        if part["mode"] == PART_ALLOW:
            return part
    if parts:
        return parts[0]
    stage = _normalize_stage(config.get("stage"), fallback_stage)
    curve = _normalize_curve(config.get("curve") or STAGE_DEFAULT_CURVES.get(stage, CURVE_SMOOTH))
    return {"stage": stage, "mode": PART_ALLOW, "curve": curve, "strength": _to_float(config.get("strength", 1.0), 1.0)}


def _template_preset_value(config: dict) -> str:
    parts = _template_parts(config)
    if len(parts) == 1:
        preset_name = _part_preset_name(parts[0])
        if preset_name:
            return preset_name
    return _part_preset_name(_primary_template_part(config)) or PRESET_CHARACTER_ALLOW


def _parts_from_presets(presets) -> tuple[list[dict], str | None]:
    selected = [str(item).strip() for item in (presets or []) if str(item).strip()]
    if not selected:
        return [], _t("preset_required")

    stages = {}
    parts = []
    for preset in selected:
        part = _normalize_template_part(preset)
        if part is None:
            return [], _t("unknown_preset").format(preset=preset)
        stage_modes = stages.setdefault(part["stage"], set())
        opposite = PART_BAN if part["mode"] == PART_ALLOW else PART_ALLOW
        if opposite in stage_modes:
            return [], _t("combo_conflict").format(stage=_display_stage(part["stage"]))
        stage_modes.add(part["mode"])
        parts.append(part)

    return parts, None


def _presets_from_template(name: str) -> list[str]:
    config = _template_config(name)
    parts = _template_parts(config)
    presets = [_part_preset_name(part) for part in parts]
    presets = [preset for preset in presets if preset]
    if presets:
        return presets
    return [_template_preset_value(config)]


def _builder_presets_from_template(name: str) -> list[str]:
    return [_display_preset(preset) for preset in _presets_from_template(name)]


def _template_stage_from_name(name: str, fallback=STAGE_CHARACTER) -> str:
    config = _template_config(name)
    primary_part = _primary_template_part(config, fallback)
    stage = primary_part["stage"]
    return stage if stage in STAGE_CHOICES else fallback


def _auto_stage_values(stage: str, shift_value) -> tuple[float, float, float, float]:
    stage = _normalize_stage(stage, STAGE_CHARACTER)
    shift = _clamp(_to_float(shift_value, 3.0), 1.0, 24.0)
    # Shift 3.0 is Forge's common default. Higher Shift usually keeps useful
    # structure later in the denoise path, so template windows move slightly later.
    move = _clamp((shift - 3.0) / 21.0, -0.10, 1.0) * 0.12

    if stage == STAGE_COMPOSITION:
        start = 0.0
        end = _clamp(0.32 + move, 0.22, 0.46)
        peak = _clamp(0.08 + move * 0.25, start, end)
        strength = 1.0
    elif stage == STAGE_STYLE:
        start = _clamp(0.62 + move, 0.48, 0.82)
        end = 1.0
        peak = _clamp(0.86 + move * 0.35, start, end)
        strength = 1.0
    else:
        start = _clamp(0.20 + move * 0.65, 0.12, 0.36)
        end = _clamp(0.74 + move * 0.45, 0.58, 0.88)
        peak = _clamp((start + end) * 0.5, start, end)
        strength = 1.0

    return start, end, peak, strength


def _apply_template_ui(template_name, shift_value):
    config = _template_config(template_name)
    primary_part = _primary_template_part(config)
    auto = bool(config.get("auto", True))
    curve = _normalize_curve(config.get("curve") or primary_part.get("curve") or CURVE_SMOOTH)

    if auto:
        start, end, peak, strength = _auto_stage_values(primary_part["stage"], shift_value)
    else:
        start = _clamp(_to_float(config.get("start"), 0.2), 0.0, 1.0)
        end = _clamp(_to_float(config.get("end"), 0.8), 0.0, 1.0)
        if end < start:
            start, end = end, start
        peak = _clamp(_to_float(config.get("peak"), (start + end) * 0.5), start, end)
        strength = _clamp(_to_float(config.get("strength"), 1.0), 0.0, 4.0)

    return (
        gr.update(value=auto),
        gr.update(value=round(start, 4)),
        gr.update(value=round(end, 4)),
        gr.update(value=round(peak, 4)),
        gr.update(value=round(strength, 4)),
        gr.update(value=_display_curve(curve)),
    )


def _auto_timing_ui(template_name, shift_value, auto, start, end, peak, strength):
    if not auto:
        return gr.update(value=start), gr.update(value=end), gr.update(value=peak), gr.update(value=strength)

    config = _template_config(template_name)
    primary_part = _primary_template_part(config)
    start, end, peak, strength = _auto_stage_values(primary_part["stage"], shift_value)
    return (
        gr.update(value=round(start, 4)),
        gr.update(value=round(end, 4)),
        gr.update(value=round(peak, 4)),
        gr.update(value=round(strength, 4)),
    )


def _save_template_ui(name, auto, template_name, start, end, peak, strength, curve):
    name = str(name or "").strip()
    if not name:
        return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), _t("template_name_required")
    logical_name = _normalize_template_name(name)
    if logical_name in BUILTIN_TEMPLATES:
        return _template_dropdown_update(logical_name), _template_dropdown_update(logical_name), _template_dropdown_update(logical_name), _t("builtin_template_locked")

    data = _load_custom_templates()
    template_name = _normalize_template_name(template_name)
    stage = _template_stage_from_name(template_name)
    source_parts = _template_parts(_template_config(template_name))
    data[name] = {
        "auto": bool(auto),
        "stage": stage if stage in STAGE_CHOICES else STAGE_CHARACTER,
        "start": _clamp(_to_float(start), 0.0, 1.0),
        "end": _clamp(_to_float(end), 0.0, 1.0),
        "peak": _clamp(_to_float(peak), 0.0, 1.0),
        "strength": _clamp(_to_float(strength, 1.0), 0.0, 4.0),
        "curve": _normalize_curve(curve),
    }
    if source_parts:
        data[name]["parts"] = source_parts
    _save_custom_templates(data)
    return _template_dropdown_update(name), _template_dropdown_update(name), _template_dropdown_update(name), _t("template_saved").format(name=name)


def _save_preset_combo_template_ui(name, selected_presets, shift_value=3.0):
    name = str(name or "").strip()
    if not name:
        return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), _t("template_name_required")
    logical_name = _normalize_template_name(name)
    if logical_name in BUILTIN_TEMPLATES:
        return _template_dropdown_update(logical_name), _template_dropdown_update(logical_name), _template_dropdown_update(logical_name), _t("builtin_preset_locked")

    parts, error = _parts_from_presets(selected_presets)
    if error:
        return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), error

    primary = next((part for part in parts if part["mode"] == PART_ALLOW), parts[0])
    start, end, peak, strength = _auto_stage_values(primary["stage"], 3.0)
    data = _load_custom_templates()
    data[name] = {
        "auto": True,
        "stage": primary["stage"],
        "parts": parts,
        "start": start,
        "end": end,
        "peak": peak,
        "strength": strength,
        "curve": primary.get("curve", STAGE_DEFAULT_CURVES.get(primary["stage"], CURVE_SMOOTH)),
    }
    _save_custom_templates(data)
    presets_text = " + ".join(_part_preset_display_name(part) for part in parts)
    preview = _preset_combo_preview_text(selected_presets, shift_value)
    return (
        _template_dropdown_update(name),
        _template_dropdown_update(name),
        _template_dropdown_update(name),
        _t("combo_saved").format(name=name, presets=presets_text, preview=preview),
    )


def _open_template_builder_ui(template_name, shift_value):
    presets = _builder_presets_from_template(template_name)
    current = _normalize_template_name(template_name)
    default_name = "" if current in BUILTIN_TEMPLATES else current
    shift = _to_float(shift_value, 3.0)
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(value=default_name),
        gr.update(value=presets),
        gr.update(value=shift),
        _preset_combo_preview_text(presets, shift),
    )


def _close_template_modal_ui():
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def _open_template_help_ui(template_name, shift_value):
    return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), _template_help_ui(template_name, shift_value)


def _preset_combo_preview_text(selected_presets, shift_value=3.0):
    parts, error = _parts_from_presets(selected_presets)
    if error:
        return error
    shift = _to_float(shift_value, 3.0)
    lines = [
        _t("combo_current") + " + ".join(_part_preset_display_name(part) for part in parts),
        "",
        f"{_t('intervention_preview')} (Shift `{_format_float(shift)}`):",
        "",
        f"| {_t('table_preset')} | {_t('table_action')} | {_t('table_start')} | {_t('table_end')} | {_t('table_peak')} | {_t('table_strength')} | {_t('table_curve')} |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for part in parts:
        start, end, peak, strength = _auto_stage_values(part["stage"], shift)
        action = _t("allow_action") if part["mode"] == PART_ALLOW else _t("ban_action")
        curve = _normalize_curve(part.get("curve") or STAGE_DEFAULT_CURVES.get(part["stage"], CURVE_SMOOTH))
        part_strength = _clamp(_to_float(part.get("strength", strength), strength), 0.0, 4.0)
        if part["mode"] == PART_BAN:
            strength_text = _t("zero_in_window")
        else:
            strength_text = _format_float(part_strength)
        lines.append(
            "| {name} | {action} | {start} | {end} | {peak} | {strength} | {curve} |".format(
                name=_part_preset_display_name(part),
                action=action,
                start=_format_float(start),
                end=_format_float(end),
                peak=_format_float(peak),
                strength=strength_text,
                curve=_display_curve(curve),
            )
        )
    return "\n".join(lines)


def _preset_combo_status_ui(selected_presets, shift_value=3.0):
    return _preset_combo_preview_text(selected_presets, shift_value)


def _template_help_ui(template_name, shift_value):
    config = _template_config(template_name)
    if not config:
        config = _template_config(PRESET_CHARACTER_ALLOW)
    parts = _template_parts(config)
    if not parts:
        parts = [_primary_template_part(config)]

    shift = _to_float(shift_value, 3.0)
    lines = [
        _t("help_title"),
        "",
        _t("help_line_templates"),
        _t("help_line_shift"),
        _t("help_line_combo"),
        _t("help_line_ratios"),
        "",
        f"{_t('current_template')}: `{_display_template_name(template_name)}`",
        f"{_t('current_shift')}: `{_format_float(shift)}`",
        "",
        _t("template_parts"),
    ]
    for part in parts:
        start, end, peak, strength = _auto_stage_values(part["stage"], shift)
        action = _t("allow_action") if part["mode"] == PART_ALLOW else _t("ban_action")
        lines.append(
            _t("help_part_line").format(
                preset=_part_preset_display_name(part),
                stage=_display_stage(part["stage"]),
                action=action,
                start=_format_float(start),
                end=_format_float(end),
                peak=_format_float(peak),
                strength=_format_float(strength),
            )
        )

    return gr.update(value="\n".join(lines), visible=True)


def _rename_template_ui(old_name, new_name):
    old_name = _normalize_template_name(old_name)
    new_name = str(new_name or "").strip()
    if not old_name:
        return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), _t("no_template_selected")
    if old_name in BUILTIN_TEMPLATES:
        return _template_dropdown_update(old_name), _template_dropdown_update(old_name), _template_dropdown_update(old_name), _t("builtin_template_rename_locked")
    if not new_name:
        return _template_dropdown_update(old_name), _template_dropdown_update(old_name), _template_dropdown_update(old_name), _t("new_name_required")
    if _normalize_template_name(new_name) in BUILTIN_TEMPLATES:
        return _template_dropdown_update(old_name), _template_dropdown_update(old_name), _template_dropdown_update(old_name), _t("builtin_name_forbidden")
    if new_name == old_name:
        return _template_dropdown_update(new_name), _template_dropdown_update(new_name), _template_dropdown_update(new_name), _t("same_name")

    data = _load_custom_templates()
    if old_name not in data:
        return _template_dropdown_update(old_name), _template_dropdown_update(old_name), _template_dropdown_update(old_name), _t("template_missing")
    if new_name in data:
        return _template_dropdown_update(old_name), _template_dropdown_update(old_name), _template_dropdown_update(old_name), _t("target_name_exists")

    data[new_name] = data.pop(old_name)
    _save_custom_templates(data)
    return (
        _template_dropdown_update(new_name),
        _template_dropdown_update(new_name),
        _template_dropdown_update(new_name),
        _t("template_renamed").format(old_name=old_name, new_name=new_name),
    )


def _delete_template_ui(name):
    name = _normalize_template_name(name)
    if not name:
        return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), _t("no_template_selected")
    if name in BUILTIN_TEMPLATES:
        return _template_dropdown_update(name), _template_dropdown_update(name), _template_dropdown_update(name), _t("builtin_template_delete_locked")

    data = _load_custom_templates()
    if name in data:
        del data[name]
        _save_custom_templates(data)
    return _template_dropdown_update(), _template_dropdown_update(), _template_dropdown_update(), _t("template_deleted").format(name=name)


def _layer_weight_module():
    for module in getattr(script_loading, "loaded_scripts", {}).values():
        if hasattr(module, "_is_anima_adapter_file") and hasattr(module, "_names_for_lora_file"):
            return module
    for module in list(sys.modules.values()):
        if hasattr(module, "_is_anima_adapter_file") and hasattr(module, "_names_for_lora_file"):
            return module
    return None


def _names_for_lora_file(filename) -> set[str]:
    layer_module = _layer_weight_module()
    if layer_module is not None:
        try:
            return set(layer_module._names_for_lora_file(filename))
        except Exception:
            pass

    path = Path(str(filename or ""))
    names = {str(path).lower(), path.name.lower(), path.stem.lower()}
    try:
        import networks

        for name, entry in getattr(networks, "available_networks", {}).items():
            try:
                if os.path.abspath(str(entry.filename)) == os.path.abspath(str(filename)):
                    names.add(str(name).lower())
                    names.add(str(getattr(entry, "alias", "")).lower())
                    names.add(str(entry.get_alias()).lower())
            except Exception:
                continue
    except Exception:
        pass
    return {x for x in names if x}


def _resolve_lora_filename(name: str):
    key = str(name or "").strip()
    if not key:
        return None
    try:
        import networks

        entry = None
        if key.lower() in getattr(networks, "forbidden_network_aliases", set()):
            entry = getattr(networks, "available_networks", {}).get(key)
        if entry is None:
            entry = getattr(networks, "available_network_aliases", {}).get(key)
        if entry is None:
            entry = getattr(networks, "available_networks", {}).get(key)
        if entry is None and hasattr(networks, "update_available_networks_by_names"):
            networks.update_available_networks_by_names([key])
            entry = getattr(networks, "available_network_aliases", {}).get(key) or getattr(networks, "available_networks", {}).get(key)
        return getattr(entry, "filename", None) if entry is not None else None
    except Exception:
        return None


def _is_anima_lora_file(filename) -> bool:
    if not filename:
        return False

    layer_module = _layer_weight_module()
    if layer_module is not None:
        try:
            return bool(layer_module._is_anima_adapter_file(filename, "lora"))
        except Exception:
            pass

    path = Path(str(filename))
    if path.suffix.lower() != ".safetensors" or not path.exists():
        return False

    try:
        from safetensors import safe_open

        with safe_open(str(path), framework="pt", device="cpu") as f:
            for key in f.keys():
                lower = key.lower()
                if "qwen3_06b" in lower:
                    return True
                if "diffusion_model.net.blocks." in lower or "diffusion_model.blocks." in lower:
                    return True
                if re.search(r"(?:^|\.)blocks\.\d+\.", lower) and ("lora" in lower or "lokr" in lower):
                    return True
    except Exception:
        return False
    return False


def _is_unet_patch_key(key) -> bool:
    text = str(key or "").lower()
    if "qwen" in text or "text_encoder" in text or "text_encoders" in text:
        return False
    return text.startswith("diffusion_model.") or ".blocks." in text or "blocks_" in text


def _activation_pass_for_extra_network_data(state, extra_network_data) -> str | None:
    p = state.p
    if getattr(p, "enable_hr", False) and getattr(p, "hr_extra_network_data", None) is extra_network_data:
        return "hires"
    if getattr(p, "extra_network_data", None) is extra_network_data:
        return "base"
    return None


def _prepare_for_extra_network_activation(p, extra_network_data):
    state = getattr(p, "_anima_lora_stage_scheduler_state", None)
    if state is None or not state.enabled or getattr(p, "sd_model", None) is None:
        return None

    pass_name = _activation_pass_for_extra_network_data(state, extra_network_data)
    if pass_name == "hires":
        p.sd_model.current_lora_hash = f"anima-stage-scheduler:activate-hires:{state.signature}:batch={getattr(p, 'iteration', 0)}"
    elif pass_name == "base":
        p.sd_model.current_lora_hash = f"anima-stage-scheduler:activate-base:{state.signature}:batch={getattr(p, 'iteration', 0)}"
    return pass_name


def _sampling_progress(step, total_steps) -> float:
    if total_steps <= 1:
        return 0.0
    return _clamp(float(step) / float(total_steps - 1), 0.0, 1.0)


def _curve_factor_for_window(progress, start, end, peak, strength, curve) -> float:
    curve = _normalize_curve(curve)
    start = _clamp(start, 0.0, 1.0)
    end = _clamp(end, 0.0, 1.0)
    if end < start:
        start, end = end, start

    if progress < start or progress > end:
        return 0.0

    strength = _clamp(strength, 0.0, 4.0)
    if strength == 0.0:
        return 0.0

    span = max(end - start, 1e-6)
    local = _clamp((progress - start) / span, 0.0, 1.0)

    if curve == CURVE_HOLD:
        factor = 1.0
    elif curve == CURVE_FRONT:
        factor = 1.0 - local
    elif curve == CURVE_BACK:
        factor = local
    else:
        peak = _clamp(peak, start, end)
        peak_local = _clamp((peak - start) / span, 0.0, 1.0)
        if local <= peak_local:
            factor = local / max(peak_local, 1e-6)
        else:
            factor = (1.0 - local) / max(1.0 - peak_local, 1e-6)
        factor = _clamp(factor, 0.0, 1.0)
        if curve == CURVE_SMOOTH:
            factor = factor * factor * (3.0 - 2.0 * factor)

    return _clamp(factor * strength, 0.0, 4.0)


def _stage_curve_factor(config, step, total_steps) -> float:
    progress = _sampling_progress(step, total_steps)
    if config.parts:
        allow_factors = []
        ban_active = False

        for part in config.parts:
            start, end, peak, strength = _auto_stage_values(part["stage"], config.shift)
            curve = _normalize_curve(part.get("curve") or STAGE_DEFAULT_CURVES.get(part["stage"], CURVE_SMOOTH))
            part_strength = _clamp(_to_float(part.get("strength", strength), strength), 0.0, 4.0)

            if part["mode"] == PART_BAN:
                window_start, window_end = (start, end) if start <= end else (end, start)
                if window_start <= progress <= window_end:
                    ban_active = True
                continue

            allow_factors.append(_curve_factor_for_window(progress, start, end, peak, part_strength, curve))

        factor = max(allow_factors) if allow_factors else _clamp(config.stage_strength, 0.0, 4.0)
        return 0.0 if ban_active else _clamp(factor, 0.0, 4.0)

    return _curve_factor_for_window(progress, config.start, config.end, config.peak, config.stage_strength, config.curve)


@dataclass
class PassConfig:
    target_mode: str
    target_loras: str
    panel_weight: PanelWeightSpec
    template_name: str
    lora_templates_text: str
    lora_templates: dict[str, str]
    auto_timing: bool
    stage: str
    parts: list[dict]
    start: float
    end: float
    peak: float
    stage_strength: float
    curve: str
    shift: float
    prompt_names: set[str] = field(default_factory=set)
    _lora_template_cache: dict = field(default_factory=dict, init=False, repr=False)

    @property
    def panel_weight_nonzero(self) -> bool:
        return self.panel_weight.active

    @property
    def targets(self) -> set[str]:
        return _parse_targets(self.target_loras)

    def finalize_timing(self):
        self.template_name = _normalize_template_name(self.template_name)
        template = _template_config(self.template_name)
        self.parts = _template_parts(template)
        stage = _normalize_stage(template.get("stage") or _stage_from_template_value(self.stage), STAGE_CHARACTER)
        if self.parts:
            primary = next((part for part in self.parts if part["mode"] == PART_ALLOW), self.parts[0])
            stage = primary["stage"]
        self.stage = stage

        if self.auto_timing:
            self.start, self.end, self.peak, self.stage_strength = _auto_stage_values(stage, self.shift)
        else:
            self.start = _clamp(_to_float(self.start), 0.0, 1.0)
            self.end = _clamp(_to_float(self.end), 0.0, 1.0)
            if self.end < self.start:
                self.start, self.end = self.end, self.start
            self.peak = _clamp(_to_float(self.peak), self.start, self.end)
            self.stage_strength = _clamp(_to_float(self.stage_strength, 1.0), 0.0, 4.0)

        self.curve = _normalize_curve(self.curve)

    def config_for_file(self, filename):
        names = _names_for_lora_file(filename)
        template_name = None
        for selector_name, selector_template in self.lora_templates.items():
            if selector_name in names:
                template_name = _normalize_template_name(selector_template)
                break

        if not template_name or template_name == self.template_name:
            return self

        cache_key = _normalize_name(template_name)
        cached = self._lora_template_cache.get(cache_key)
        if cached is not None:
            return cached

        template = _template_config(template_name)
        auto_timing = bool(template.get("auto", self.auto_timing))
        parts = _template_parts(template)
        stage = _normalize_stage(template.get("stage") or self.stage, self.stage)
        if parts:
            primary = next((part for part in parts if part["mode"] == PART_ALLOW), parts[0])
            stage = primary["stage"]
        curve = _normalize_curve(template.get("curve") or self.curve)
        start = template.get("start", self.start) if not auto_timing else self.start
        end = template.get("end", self.end) if not auto_timing else self.end
        peak = template.get("peak", self.peak) if not auto_timing else self.peak
        stage_strength = template.get("strength", self.stage_strength) if not auto_timing else self.stage_strength

        config = PassConfig(
            target_mode=self.target_mode,
            target_loras=self.target_loras,
            panel_weight=self.panel_weight,
            template_name=template_name,
            lora_templates_text=self.lora_templates_text,
            lora_templates=self.lora_templates,
            auto_timing=auto_timing,
            stage=stage,
            parts=parts,
            start=start,
            end=end,
            peak=peak,
            stage_strength=stage_strength,
            curve=curve,
            shift=self.shift,
            prompt_names=self.prompt_names,
        )
        config.finalize_timing()
        self._lora_template_cache[cache_key] = config
        return config

    def prompt_name_matches(self, lora_name: str) -> bool:
        if self.target_mode == MODE_PROMPT_ALL:
            return True
        if self.target_mode == MODE_TARGETS:
            name = _normalize_name(lora_name)
            names = {name, Path(name).name.lower(), Path(name).stem.lower()}
            return bool(names & self.targets)

        filename = _resolve_lora_filename(lora_name)
        return _is_anima_lora_file(filename)

    def file_matches(self, filename) -> bool:
        names = _names_for_lora_file(filename)
        if self.target_mode == MODE_PROMPT_ALL:
            return bool(names & self.prompt_names) if self.prompt_names else True
        if self.target_mode == MODE_TARGETS:
            return bool(names & self.targets)
        return _is_anima_lora_file(filename)


class ScheduledStrength:
    def __init__(self, base_strength, config: PassConfig, pass_name: str):
        self.base_strength = _to_float(base_strength, 1.0)
        self.config = config
        self.pass_name = pass_name
        self.factor = 1.0

    def value(self) -> float:
        return float(self.base_strength) * float(self.factor)

    def __float__(self):
        return self.value()

    def __bool__(self):
        return self.value() != 0.0

    def __repr__(self):
        return _format_float(self.value())

    def __eq__(self, other):
        return self.value() == other

    def __ne__(self, other):
        return self.value() != other

    def __mul__(self, other):
        return self.value() * other

    def __rmul__(self, other):
        return other * self.value()

    def __truediv__(self, other):
        return self.value() / other

    def __rtruediv__(self, other):
        return other / self.value()


@dataclass
class RuntimeState:
    p: object
    run_id: str
    enabled: bool
    base: PassConfig
    hires: PassConfig
    hr_disable_mode: str
    hr_disable_tags: list[str]
    original_online_lora: bool
    current_activation_pass: str | None = None
    wrappers: list[ScheduledStrength] = field(default_factory=list)
    warned_offline: bool = False

    def current_config(self) -> PassConfig:
        pass_name = self.current_pass_name()
        if pass_name == "hires":
            return self.hires
        return self.base

    def current_pass_name(self) -> str:
        if self.current_activation_pass in {"base", "hires"}:
            return self.current_activation_pass
        if bool(getattr(self.p, "is_hr_pass", False)):
            return "hires"
        return "base"

    def register(self, wrapper: ScheduledStrength):
        self.wrappers.append(wrapper)

    def set_factor(self, factor: float):
        for wrapper in self.wrappers:
            wrapper.factor = factor

    @property
    def signature(self) -> str:
        return "|".join(
            [
                self.run_id,
                self.base.target_mode,
                self.base.target_loras,
                _compact_text(self.base.panel_weight.raw),
                self.base.template_name,
                _compact_text(self.base.lora_templates_text),
                self.hires.target_mode,
                self.hires.target_loras,
                _compact_text(self.hires.panel_weight.raw),
                self.hires.template_name,
                _compact_text(self.hires.lora_templates_text),
                self.hr_disable_mode,
            ]
        )


def _build_pass_config(target_mode, target_loras, panel_weight, template_name, lora_templates_text, auto_timing, stage, start, end, peak, stage_strength, curve, shift):
    target_mode = _normalize_target_mode(target_mode)
    template_name = _normalize_template_name(template_name or next(iter(BUILTIN_TEMPLATES)))
    config = PassConfig(
        target_mode=target_mode,
        target_loras=str(target_loras or ""),
        panel_weight=_parse_panel_weight(panel_weight),
        template_name=template_name,
        lora_templates_text=str(lora_templates_text or ""),
        lora_templates=_parse_lora_template_overrides(lora_templates_text),
        auto_timing=bool(auto_timing),
        stage=_stage_from_template_value(stage),
        parts=[],
        start=_to_float(start, 0.2),
        end=_to_float(end, 0.8),
        peak=_to_float(peak, 0.5),
        stage_strength=_to_float(stage_strength, 1.0),
        curve=_normalize_curve(curve),
        shift=_to_float(shift, 3.0),
    )
    config.finalize_timing()
    return config


def _remove_hires_lora_tags(p, state: RuntimeState):
    if not getattr(p, "enable_hr", False) or not hasattr(p, "all_hr_prompts") or not p.all_hr_prompts:
        return

    mode = state.hr_disable_mode
    if mode == DISABLE_NONE:
        return

    tags = state.hr_disable_tags

    def rewrite(prompt):
        text = str(prompt or "")
        if mode == DISABLE_ALL:
            return LORA_TAG_RE.sub("", text)
        if mode == DISABLE_SELECTED:
            for tag in tags:
                text = text.replace(tag, "")
        return text

    p.all_hr_prompts = [rewrite(prompt) for prompt in p.all_hr_prompts]


def _collect_prompt_names(prompts) -> set[str]:
    names = set()
    for prompt in prompts or []:
        for match in LORA_TAG_RE.finditer(str(prompt or "")):
            name = _normalize_name(match.group(1))
            if name:
                names.add(name)
                names.add(Path(name).name.lower())
                names.add(Path(name).stem.lower())
    return names


def _rewrite_prompt_loras(prompts, config: PassConfig):
    rewritten = []

    def replace(match):
        name = match.group(1).strip()
        if config.panel_weight_nonzero and config.prompt_name_matches(name):
            return f"<lora:{name}:{_format_float(config.panel_weight.prompt_multiplier())}>"
        return match.group(0)

    for prompt in prompts or []:
        rewritten.append(LORA_TAG_RE.sub(replace, str(prompt or "")))
    return rewritten


def _rewrite_batch_prompts(p, state: RuntimeState):
    start = getattr(p, "iteration", 0) * getattr(p, "batch_size", 1)
    end = start + getattr(p, "batch_size", 1)

    if hasattr(p, "prompts") and p.prompts:
        p.prompts = _rewrite_prompt_loras(p.prompts, state.base)
        state.base.prompt_names.update(_collect_prompt_names(p.prompts))

    if hasattr(p, "all_prompts") and p.all_prompts:
        current = _rewrite_prompt_loras(p.all_prompts[start:end], state.base)
        p.all_prompts[start:end] = current
        state.base.prompt_names.update(_collect_prompt_names(current))

    if getattr(p, "enable_hr", False) and hasattr(p, "all_hr_prompts") and p.all_hr_prompts:
        current = _rewrite_prompt_loras(p.all_hr_prompts[start:end], state.hires)
        p.all_hr_prompts[start:end] = current
        state.hires.prompt_names.update(_collect_prompt_names(current))

    if getattr(p, "enable_hr", False) and hasattr(p, "hr_prompts") and p.hr_prompts:
        p.hr_prompts = _rewrite_prompt_loras(p.hr_prompts, state.hires)
        state.hires.prompt_names.update(_collect_prompt_names(p.hr_prompts))


def _patch_added_strengths(patch_destination, before_counts, state: RuntimeState, config: PassConfig, online_mode):
    pass_name = state.current_pass_name()
    for key, current_patches in patch_destination.items():
        start = before_counts.get(key, 0)
        if start >= len(current_patches):
            continue

        for index in range(start, len(current_patches)):
            patch = current_patches[index]
            if not isinstance(patch, tuple) or len(patch) < 5:
                continue

            strength_patch, patch_value, strength_model, offset, function = patch[:5]
            model_key = _model_key(key)
            base_strength = config.panel_weight.strength_for_key(model_key, strength_patch) if config.panel_weight_nonzero else strength_patch

            if _is_unet_patch_key(model_key):
                if online_mode:
                    strength_obj = ScheduledStrength(base_strength, config, pass_name)
                    state.register(strength_obj)
                    strength_patch = strength_obj
                else:
                    if not state.warned_offline:
                        logger.warning("Anima stage scheduler needs Forge online LoRA for per-step strength control.")
                        state.warned_offline = True
                    strength_patch = _to_float(base_strength, 1.0)
            elif config.panel_weight_nonzero:
                strength_patch = _to_float(base_strength, 1.0)
            else:
                strength_patch = base_strength

            current_patches[index] = (strength_patch, patch_value, strength_model, offset, function)


def install_patch():
    global _ORIGINAL_ADD_PATCHES, _ORIGINAL_EXTRA_NETWORKS_ACTIVATE

    from backend.patcher.base import ModelPatcher
    from modules import extra_networks

    if not getattr(ModelPatcher.add_patches, "_anima_stage_scheduler_patched", False):
        _ORIGINAL_ADD_PATCHES = ModelPatcher.add_patches

        def add_patches_with_stage_scheduler(self, patches: list[dict], strength_patch: float = 1.0, strength_model: float = 1.0, *, filename: str = None, online_mode: bool = None):
            state = _ACTIVE_STATE
            config = state.current_config() if state is not None and state.enabled else None
            should_control = config is not None and config.file_matches(filename)
            lora_config = config.config_for_file(filename) if should_control else None

            patch_destination = self.online_patches if online_mode else self.patches
            before_counts = {key: len(value) for key, value in patch_destination.items()} if should_control else {}

            loaded = _ORIGINAL_ADD_PATCHES(self, patches, strength_patch=strength_patch, strength_model=strength_model, filename=filename, online_mode=online_mode)

            if should_control:
                _patch_added_strengths(patch_destination, before_counts, state, lora_config, bool(online_mode))

            return loaded

        add_patches_with_stage_scheduler._anima_stage_scheduler_patched = True
        ModelPatcher.add_patches = add_patches_with_stage_scheduler
        logger.info("Installed Anima LoRA stage scheduler patch")

    if not getattr(extra_networks.activate, "_anima_stage_scheduler_patched", False):
        _ORIGINAL_EXTRA_NETWORKS_ACTIVATE = extra_networks.activate

        def activate_with_stage_scheduler(p, extra_network_data):
            state = getattr(p, "_anima_lora_stage_scheduler_state", None)
            previous_pass = getattr(state, "current_activation_pass", None) if state is not None else None
            pass_name = _prepare_for_extra_network_activation(p, extra_network_data)
            if state is not None and pass_name is not None:
                state.current_activation_pass = pass_name
            try:
                return _ORIGINAL_EXTRA_NETWORKS_ACTIVATE(p, extra_network_data)
            finally:
                if state is not None:
                    state.current_activation_pass = previous_pass

        activate_with_stage_scheduler._anima_stage_scheduler_patched = True
        extra_networks.activate = activate_with_stage_scheduler
        logger.info("Installed Anima LoRA stage scheduler extra network patch")


def _denoiser_callback(params):
    state = _ACTIVE_STATE
    if state is None or not state.enabled:
        return

    denoiser = getattr(params, "denoiser", None)
    p = getattr(denoiser, "p", None)
    if p is None or p is not state.p:
        return

    pass_name = state.current_pass_name()
    for wrapper in state.wrappers:
        if wrapper.pass_name == pass_name:
            wrapper.factor = _stage_curve_factor(wrapper.config, params.sampling_step, params.total_sampling_steps)
        else:
            wrapper.factor = 0.0


def _register_cfg_callback_once():
    global _CFG_CALLBACK_REGISTERED
    if _CFG_CALLBACK_REGISTERED:
        return
    script_callbacks.on_cfg_denoiser(_denoiser_callback, name="anima_lora_stage_scheduler")
    _CFG_CALLBACK_REGISTERED = True


class Script(scripts.Script):
    section = None

    def __init__(self):
        _register_cfg_callback_once()
        self.base_shift_component = None
        self.hires_shift_component = None

    def title(self):
        return _t("title")

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def after_component(self, component, **kwargs):
        elem_id = kwargs.get("elem_id")
        if self.is_txt2img:
            if elem_id == "txt2img_distilled_cfg_scale":
                self.base_shift_component = component
            elif elem_id == "txt2img_hr_distilled_cfg":
                self.hires_shift_component = component
        elif self.is_img2img and elem_id == "img2img_distilled_cfg_scale":
            self.base_shift_component = component

    def _stage_panel(self, prefix: str, label: str, default_open: bool, default_target_mode=MODE_AUTO_ANIMA):
        choices = _template_choice_names()
        default_template = choices[0] if choices else _display_template_name(PRESET_CHARACTER_ALLOW)

        with gr.Accordion(label, open=default_open, elem_id=self.elem_id(f"{prefix}_panel")):
            with gr.Row():
                target_mode = gr.Radio(_target_mode_choices(), value=_display_target_mode(default_target_mode), label=_t("target_scope"), elem_id=self.elem_id(f"{prefix}_target_mode"))
                panel_weight = gr.Textbox(
                    label=_t("panel_weight"),
                    value="0",
                    lines=1,
                    placeholder="0.8 or 0-18=1,19-27=0.2 or blocks=0-18=1,19-27=0.2;modules=mlp=0.8",
                    elem_id=self.elem_id(f"{prefix}_panel_weight"),
                )
            target_loras = gr.Textbox(label=_t("target_lora"), value="", lines=1, placeholder=_t("target_lora_placeholder"), elem_id=self.elem_id(f"{prefix}_target_loras"))

            with gr.Row():
                template = gr.Dropdown(label=_t("template"), choices=choices, value=default_template, elem_id=self.elem_id(f"{prefix}_template"))
                copy_template = gr.Button(_t("copy"), elem_id=self.elem_id(f"{prefix}_copy_template"))
                help_template = gr.Button("?", elem_id=self.elem_id(f"{prefix}_template_help"))
                open_builder = gr.Button(_t("builder"), elem_id=self.elem_id(f"{prefix}_open_template_builder"))
            auto_timing = gr.Checkbox(label=_t("auto_timing"), value=True, elem_id=self.elem_id(f"{prefix}_auto_timing"))
            lora_templates = gr.Textbox(
                label=_t("single_lora_template"),
                value="",
                lines=3,
                placeholder=_t("single_lora_template_placeholder"),
                elem_id=self.elem_id(f"{prefix}_lora_templates"),
            )

            with gr.Row():
                start = gr.Slider(0.0, 1.0, value=0.62 if prefix == "base" else 0.20, step=0.01, label=_t("start"), elem_id=self.elem_id(f"{prefix}_start"))
                end = gr.Slider(0.0, 1.0, value=1.0 if prefix == "base" else 0.74, step=0.01, label=_t("end"), elem_id=self.elem_id(f"{prefix}_end"))
                peak = gr.Slider(0.0, 1.0, value=0.86 if prefix == "base" else 0.48, step=0.01, label=_t("peak"), elem_id=self.elem_id(f"{prefix}_peak"))

            with gr.Row():
                stage_strength = gr.Slider(0.0, 2.0, value=1.0, step=0.01, label=_t("strength"), elem_id=self.elem_id(f"{prefix}_stage_strength"))
                curve = gr.Dropdown(label=_t("curve"), choices=_curve_choices(), value=_display_curve(CURVE_SMOOTH), elem_id=self.elem_id(f"{prefix}_curve"))

        return target_mode, target_loras, panel_weight, template, lora_templates, auto_timing, start, end, peak, stage_strength, curve, copy_template, help_template, open_builder

    def ui(self, is_img2img):
        template_css = f"""
        <style>
        #{self.elem_id("template_modal")} {{
            position: fixed;
            inset: 0;
            z-index: 5000;
            padding: 24px;
            overflow: auto;
            box-sizing: border-box;
            background: rgba(0, 0, 0, 0.92);
        }}
        #{self.elem_id("template_modal")}.hide {{
            display: none !important;
        }}
        #{self.elem_id("template_modal")}:not(.hide) {{
            display: flex !important;
            align-items: center;
            justify-content: center;
        }}
        #{self.elem_id("template_modal_box")} {{
            width: min(980px, calc(100vw - 48px));
            max-height: calc(100vh - 48px);
            margin: 0 auto;
            background: #111827 !important;
            border: 1px solid #475569;
            border-radius: 8px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.65);
            padding: 16px;
            overflow: auto;
            box-sizing: border-box;
        }}
        #{self.elem_id("template_modal_box")} > .form,
        #{self.elem_id("template_help_modal")},
        #{self.elem_id("template_builder_modal")} {{
            background: #111827 !important;
        }}
        </style>
        """
        with gr.Accordion(_t("title"), open=False, elem_id=self.elem_id("accordion")):
            _intro_block(self.elem_id)
            enabled = gr.Checkbox(label=_t("enable"), value=False, elem_id=self.elem_id("enabled"))
            gr.HTML(template_css)

            base_controls = self._stage_panel("base", _t("base_panel"), True)

            with gr.Accordion(_t("hires_panel"), open=False, elem_id=self.elem_id("hires_panel")):
                hr_independent = gr.Checkbox(label=_t("hr_independent"), value=False, elem_id=self.elem_id("hr_independent"))
                hires_controls = self._stage_panel("hires", _t("hires_lora_panel"), True)
                with gr.Row():
                    hr_disable_mode = gr.Radio(_disable_choices(), value=_display_disable_mode(DISABLE_NONE), label=_t("hr_disable"), elem_id=self.elem_id("hr_disable_mode"))
                hr_disable_tags = gr.Textbox(
                    label=_t("hr_disable_tags"),
                    value="",
                    lines=3,
                    placeholder="<lora:name:0.8>\n<lora:name:blocks=0-9=0.8,10-18=1.0,19-27=0.7>",
                    elem_id=self.elem_id("hr_disable_tags"),
                )

            template_choices = _template_choice_names()
            manage_default = template_choices[0] if template_choices else None
            with gr.Accordion(_t("template_manager"), open=False, elem_id=self.elem_id("template_manager")):
                with gr.Row():
                    manage_template = gr.Dropdown(label=_t("existing_template"), choices=template_choices, value=manage_default, elem_id=self.elem_id("manage_template"))
                    rename_template_name = gr.Textbox(label=_t("rename_to"), lines=1, elem_id=self.elem_id("rename_template_name"))
                with gr.Row():
                    rename_template = gr.Button(_t("rename_template"), elem_id=self.elem_id("rename_template"))
                    delete_template = gr.Button(_t("delete_template"), elem_id=self.elem_id("delete_template"))
                with gr.Row():
                    custom_name = gr.Textbox(label=_t("new_template_name"), lines=1, elem_id=self.elem_id("custom_name"))
                    custom_auto = gr.Checkbox(label=_t("save_auto_template"), value=True, elem_id=self.elem_id("custom_auto"))
                with gr.Row():
                    save_current_template = gr.Button(_t("save_current_base"), elem_id=self.elem_id("save_template"))
                template_status = gr.Markdown(value="", elem_id=self.elem_id("template_status"))

            with gr.Group(visible=False, elem_id=self.elem_id("template_modal")) as template_modal:
                with gr.Group(elem_id=self.elem_id("template_modal_box")):
                    with gr.Group(visible=False, elem_id=self.elem_id("template_help_modal")) as template_help_modal:
                        with gr.Row():
                            gr.Markdown(_t("template_help"))
                            close_help = gr.Button(_t("close"), elem_id=self.elem_id("close_template_help"))
                        template_help = gr.Markdown(value="", elem_id=self.elem_id("template_help_text"))
                    with gr.Group(visible=False, elem_id=self.elem_id("template_builder_modal")) as template_builder:
                        with gr.Row():
                            gr.Markdown(_t("combo_title"))
                            close_builder = gr.Button(_t("close"), elem_id=self.elem_id("close_template_builder"))
                        builder_name = gr.Textbox(label=_t("template_name"), lines=1, elem_id=self.elem_id("builder_name"))
                        builder_presets = gr.CheckboxGroup(
                            label=_t("base_preset_combo"),
                            choices=_builder_preset_choices(),
                            value=[_display_preset(PRESET_CHARACTER_ALLOW)],
                            elem_id=self.elem_id("builder_presets"),
                        )
                        builder_shift = gr.Number(label=_t("preview_shift"), value=3.0, precision=4, elem_id=self.elem_id("builder_shift"))
                        with gr.Row():
                            save_combo_template = gr.Button(_t("save_combo"), variant="primary", elem_id=self.elem_id("save_combo_template"))
                        builder_status = gr.Markdown(value="", elem_id=self.elem_id("builder_status"))

        (
            base_target_mode,
            base_target_loras,
            base_panel_weight,
            base_template,
            base_lora_templates,
            base_auto,
            base_start,
            base_end,
            base_peak,
            base_stage_strength,
            base_curve,
            base_copy_template,
            base_help_template,
            base_open_builder,
        ) = base_controls
        (
            hr_target_mode,
            hr_target_loras,
            hr_panel_weight,
            hr_template,
            hr_lora_templates,
            hr_auto,
            hr_start,
            hr_end,
            hr_peak,
            hr_stage_strength,
            hr_curve,
            hr_copy_template,
            hr_help_template,
            hr_open_builder,
        ) = hires_controls

        base_shift = self.base_shift_component or gr.Number(value=3.0, visible=False)
        hires_shift = self.hires_shift_component or self.base_shift_component or gr.Number(value=3.0, visible=False)

        for template_component, shift_component, auto_component, start_component, end_component, peak_component, strength_component, curve_component, help_button, copy_button in [
            (base_template, base_shift, base_auto, base_start, base_end, base_peak, base_stage_strength, base_curve, base_help_template, base_copy_template),
            (hr_template, hires_shift, hr_auto, hr_start, hr_end, hr_peak, hr_stage_strength, hr_curve, hr_help_template, hr_copy_template),
        ]:
            template_component.change(
                fn=_apply_template_ui,
                inputs=[template_component, shift_component],
                outputs=[auto_component, start_component, end_component, peak_component, strength_component, curve_component],
                show_progress=False,
            )
            auto_component.change(
                fn=_auto_timing_ui,
                inputs=[template_component, shift_component, auto_component, start_component, end_component, peak_component, strength_component],
                outputs=[start_component, end_component, peak_component, strength_component],
                show_progress=False,
            )
            help_button.click(
                fn=_open_template_help_ui,
                inputs=[template_component, shift_component],
                outputs=[template_modal, template_help_modal, template_builder, template_help],
                show_progress=False,
            )
            copy_button.click(
                fn=None,
                _js="(value) => { if (navigator.clipboard) { navigator.clipboard.writeText(value || ''); } return []; }",
                inputs=[template_component],
                outputs=[],
                show_progress=False,
            )

        base_open_builder.click(
            fn=_open_template_builder_ui,
            inputs=[base_template, base_shift],
            outputs=[template_modal, template_help_modal, template_builder, builder_name, builder_presets, builder_shift, builder_status],
            show_progress=False,
        )
        hr_open_builder.click(
            fn=_open_template_builder_ui,
            inputs=[hr_template, hires_shift],
            outputs=[template_modal, template_help_modal, template_builder, builder_name, builder_presets, builder_shift, builder_status],
            show_progress=False,
        )
        close_builder.click(
            fn=_close_template_modal_ui,
            inputs=[],
            outputs=[template_modal, template_help_modal, template_builder],
            show_progress=False,
        )
        close_help.click(
            fn=_close_template_modal_ui,
            inputs=[],
            outputs=[template_modal, template_help_modal, template_builder],
            show_progress=False,
        )
        builder_presets.change(
            fn=_preset_combo_status_ui,
            inputs=[builder_presets, builder_shift],
            outputs=[builder_status],
            show_progress=False,
        )
        builder_shift.change(
            fn=_preset_combo_status_ui,
            inputs=[builder_presets, builder_shift],
            outputs=[builder_status],
            show_progress=False,
        )
        manage_template.change(
            fn=lambda name: gr.update(value="" if _normalize_template_name(name) in BUILTIN_TEMPLATES else _normalize_template_name(name)),
            inputs=[manage_template],
            outputs=[rename_template_name],
            show_progress=False,
        )

        if self.base_shift_component is not None:
            self.base_shift_component.change(
                fn=_auto_timing_ui,
                inputs=[base_template, self.base_shift_component, base_auto, base_start, base_end, base_peak, base_stage_strength],
                outputs=[base_start, base_end, base_peak, base_stage_strength],
                show_progress=False,
            )
            if hasattr(self.base_shift_component, "release"):
                self.base_shift_component.release(
                    fn=_auto_timing_ui,
                    inputs=[base_template, self.base_shift_component, base_auto, base_start, base_end, base_peak, base_stage_strength],
                    outputs=[base_start, base_end, base_peak, base_stage_strength],
                    show_progress=False,
                )

        if self.hires_shift_component is not None:
            self.hires_shift_component.change(
                fn=_auto_timing_ui,
                inputs=[hr_template, self.hires_shift_component, hr_auto, hr_start, hr_end, hr_peak, hr_stage_strength],
                outputs=[hr_start, hr_end, hr_peak, hr_stage_strength],
                show_progress=False,
            )
            if hasattr(self.hires_shift_component, "release"):
                self.hires_shift_component.release(
                    fn=_auto_timing_ui,
                    inputs=[hr_template, self.hires_shift_component, hr_auto, hr_start, hr_end, hr_peak, hr_stage_strength],
                    outputs=[hr_start, hr_end, hr_peak, hr_stage_strength],
                    show_progress=False,
                )

        save_current_template.click(
            fn=_save_template_ui,
            inputs=[custom_name, custom_auto, base_template, base_start, base_end, base_peak, base_stage_strength, base_curve],
            outputs=[base_template, hr_template, manage_template, template_status],
            show_progress=False,
        )
        save_combo_template.click(
            fn=_save_preset_combo_template_ui,
            inputs=[builder_name, builder_presets, builder_shift],
            outputs=[base_template, hr_template, manage_template, builder_status],
            show_progress=False,
        )
        rename_template.click(
            fn=_rename_template_ui,
            inputs=[manage_template, rename_template_name],
            outputs=[base_template, hr_template, manage_template, template_status],
            show_progress=False,
        )
        delete_template.click(
            fn=_delete_template_ui,
            inputs=[manage_template],
            outputs=[base_template, hr_template, manage_template, template_status],
            show_progress=False,
        )

        return [
            enabled,
            base_target_mode,
            base_target_loras,
            base_panel_weight,
            base_template,
            base_lora_templates,
            base_auto,
            base_start,
            base_end,
            base_peak,
            base_stage_strength,
            base_curve,
            hr_independent,
            hr_target_mode,
            hr_target_loras,
            hr_panel_weight,
            hr_template,
            hr_lora_templates,
            hr_auto,
            hr_start,
            hr_end,
            hr_peak,
            hr_stage_strength,
            hr_curve,
            hr_disable_mode,
            hr_disable_tags,
        ]

    def process(
        self,
        p,
        enabled,
        base_target_mode,
        base_target_loras,
        base_panel_weight,
        base_template,
        base_lora_templates,
        base_auto,
        base_start,
        base_end,
        base_peak,
        base_stage_strength,
        base_curve,
        hr_independent,
        hr_target_mode,
        hr_target_loras,
        hr_panel_weight,
        hr_template,
        hr_lora_templates,
        hr_auto,
        hr_start,
        hr_end,
        hr_peak,
        hr_stage_strength,
        hr_curve,
        hr_disable_mode,
        hr_disable_tags,
        *args,
    ):
        global _ACTIVE_STATE

        if not enabled:
            _ACTIVE_STATE = None
            return

        base_shift = _to_float(getattr(p, "distilled_cfg_scale", 3.0), 3.0)
        hires_shift = _to_float(getattr(p, "hr_distilled_cfg", base_shift), base_shift)

        base_config = _build_pass_config(
            base_target_mode,
            base_target_loras,
            base_panel_weight,
            base_template,
            base_lora_templates,
            base_auto,
            _template_stage_from_name(base_template),
            base_start,
            base_end,
            base_peak,
            base_stage_strength,
            base_curve,
            base_shift,
        )

        if hr_independent:
            hires_config = _build_pass_config(
                hr_target_mode,
                hr_target_loras,
                hr_panel_weight,
                hr_template,
                hr_lora_templates,
                hr_auto,
                _template_stage_from_name(hr_template),
                hr_start,
                hr_end,
                hr_peak,
                hr_stage_strength,
                hr_curve,
                hires_shift,
            )
        else:
            hires_config = _build_pass_config(
                base_target_mode,
                base_target_loras,
                base_panel_weight,
                base_template,
                base_lora_templates,
                base_auto,
                _template_stage_from_name(base_template),
                base_start,
                base_end,
                base_peak,
                base_stage_strength,
                base_curve,
                hires_shift,
            )

        state = RuntimeState(
            p=p,
            run_id=uuid.uuid4().hex,
            enabled=True,
            base=base_config,
            hires=hires_config,
            hr_disable_mode=_normalize_disable_mode(hr_disable_mode),
            hr_disable_tags=_parse_disable_tags(hr_disable_tags),
            original_online_lora=bool(dynamic_args.online_lora),
        )

        dynamic_args.online_lora = True
        p._anima_lora_stage_scheduler_state = state
        _ACTIVE_STATE = state

        _remove_hires_lora_tags(p, state)

        p.extra_generation_params["Anima LoRA Stage Scheduler"] = (
            f"base={base_config.template_name}:{base_config.start:.2f}-{base_config.end:.2f}, "
            f"hires={hires_config.template_name}:{hires_config.start:.2f}-{hires_config.end:.2f}"
        )
        if state.hr_disable_mode != DISABLE_NONE:
            p.extra_generation_params["Anima Hires LoRA Disable"] = state.hr_disable_mode

    def before_process_batch(self, p, *args, **kwargs):
        state = getattr(p, "_anima_lora_stage_scheduler_state", None)
        if state is None or not state.enabled:
            return

        install_patch()
        _rewrite_batch_prompts(p, state)
        if getattr(p, "sd_model", None) is not None:
            p.sd_model.current_lora_hash = f"anima-stage-scheduler:{state.signature}:batch={getattr(p, 'iteration', 0)}"

    def process_before_every_sampling(self, p, *args, **kwargs):
        state = getattr(p, "_anima_lora_stage_scheduler_state", None)
        if state is None or not state.enabled:
            return

        state.set_factor(0.0)
        if not getattr(p, "is_hr_pass", False) and getattr(p, "sd_model", None) is not None:
            p.sd_model.current_lora_hash = f"anima-stage-scheduler:force-hires-reload:{state.run_id}:{getattr(p, 'iteration', 0)}"

    def postprocess(self, p, processed, *args, **kwargs):
        global _ACTIVE_STATE

        state = getattr(p, "_anima_lora_stage_scheduler_state", None)
        if state is not None:
            dynamic_args.online_lora = state.original_online_lora
            state.set_factor(1.0)
            p._anima_lora_stage_scheduler_state = None
        if _ACTIVE_STATE is state:
            _ACTIVE_STATE = None
