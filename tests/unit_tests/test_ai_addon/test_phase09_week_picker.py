"""
Phase 09-01 Multi-Week Week Picker — Static source-analysis tests.

These tests read GenerateConfigPanel.vue directly and assert the presence
(or absence) of specific structural patterns required by decisions D-01
through D-07 and UX-04 sub-requirements. Static source analysis is the
correct approach here because: (a) Docker is not guaranteed up in CI,
(b) no @vue/test-utils is installed, and (c) the behaviors being verified
are structural template/script properties, not runtime dynamic behavior.

Gaps covered (UX-04 sub-requirements):
  UX-04a (D-07): <script setup lang="ts"> migration — defineNuxtComponent gone
  UX-04b: v-btn-toggle removed (value="this", value="next", "This week", "Next week" gone)
  UX-04c (D-01..D-06): v-select present with required attributes
  UX-04d: weekOptions 4-option array builder present in source
  UX-04e: getMondayOf function removed
  UX-04f: "this" | "next" enum type removed
  UX-04g: selectedWeek typed as string ref (not enum ref)
  UX-04h: weekStart computed removed; selectedWeek.value used directly in emit
  UX-04i: date-fns named import (startOfWeek, addDays, format) present
  UX-04j: Carry-forward fields (mealTypes, excludedDays, specialRequests,
           replaceAll, DAYS, action buttons, D-05 caption) all preserved
"""
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Source file paths (absolute, relative to this repo layout)
# ---------------------------------------------------------------------------
MEALIE_ROOT = Path(__file__).parents[3]  # mealie/
GENERATE_CONFIG_VUE = MEALIE_ROOT / "frontend/components/ai-meal-planner/GenerateConfigPanel.vue"


def _read(path: Path) -> str:
    assert path.exists(), f"Implementation file not found: {path}"
    return path.read_text(encoding="utf-8")


# Load once at module level (fast, pure I/O)
GENERATE_CONFIG_SOURCE = _read(GENERATE_CONFIG_VUE)


# ===========================================================================
# UX-04a (D-07): <script setup lang="ts"> migration
# ===========================================================================

class Ux04aScriptSetupMigrationTests:
    """UX-04a (D-07): Component migrated to <script setup lang="ts">; defineNuxtComponent gone."""

    def test_ux04a_script_setup_lang_ts_present(self):
        """D-07: <script setup lang="ts"> must appear exactly once."""
        count = GENERATE_CONFIG_SOURCE.count('<script setup lang="ts">')
        assert count == 1, (
            f'Expected exactly 1 occurrence of \'<script setup lang="ts">\', got {count}. '
            "D-07 requires the component to be migrated to <script setup lang=\"ts\">."
        )

    def test_ux04a_define_nuxt_component_removed(self):
        """D-07: defineNuxtComponent must not appear anywhere in the source."""
        assert "defineNuxtComponent" not in GENERATE_CONFIG_SOURCE, (
            "Found 'defineNuxtComponent' in GenerateConfigPanel.vue. "
            "D-07: the component must be migrated to <script setup lang=\"ts\">; "
            "defineNuxtComponent must be removed."
        )

    def test_ux04a_define_props_appears_exactly_once(self):
        """D-07: defineProps must appear exactly once (the typed interface call)."""
        count = GENERATE_CONFIG_SOURCE.count("defineProps")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'defineProps', got {count}. "
            "D-07: props must be declared with defineProps<Props>() exactly once."
        )

    def test_ux04a_define_emits_appears_exactly_once(self):
        """D-07: defineEmits must appear exactly once."""
        count = GENERATE_CONFIG_SOURCE.count("defineEmits")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'defineEmits', got {count}. "
            "D-07: emits must be declared with defineEmits<{...}>() exactly once."
        )

    def test_ux04a_with_defaults_appears_exactly_once(self):
        """D-07: withDefaults must wrap defineProps exactly once for the 3 boolean props."""
        count = GENERATE_CONFIG_SOURCE.count("withDefaults")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'withDefaults', got {count}. "
            "D-07: withDefaults(defineProps<Props>(), {{ ... }}) must wrap the props declaration."
        )

    def test_ux04a_setup_return_object_removed(self):
        """D-07: The setup() return object must not appear (script setup auto-exposes bindings)."""
        assert "return {" not in GENERATE_CONFIG_SOURCE, (
            "Found 'return {' in GenerateConfigPanel.vue. "
            "D-07: <script setup> auto-exposes all top-level bindings; no explicit return object needed."
        )


# ===========================================================================
# UX-04b: v-btn-toggle removed
# ===========================================================================

class Ux04bVBtnToggleRemovedTests:
    """UX-04b: v-btn-toggle and its enum values ('this'/'next') must be entirely removed."""

    def test_ux04b_v_btn_toggle_removed(self):
        """UX-04b: v-btn-toggle must not appear anywhere in the source."""
        count = GENERATE_CONFIG_SOURCE.count("v-btn-toggle")
        assert count == 0, (
            f"Found {count} occurrence(s) of 'v-btn-toggle' in GenerateConfigPanel.vue. "
            "UX-04b: the v-btn-toggle must be replaced by a v-select dropdown."
        )

    def test_ux04b_value_this_removed(self):
        """UX-04b: value=\"this\" (v-btn enum value) must not appear."""
        assert 'value="this"' not in GENERATE_CONFIG_SOURCE, (
            "Found 'value=\"this\"' in GenerateConfigPanel.vue. "
            "UX-04b: the 'this' enum value button must be removed."
        )

    def test_ux04b_value_next_removed(self):
        """UX-04b: value=\"next\" (v-btn enum value) must not appear."""
        assert 'value="next"' not in GENERATE_CONFIG_SOURCE, (
            "Found 'value=\"next\"' in GenerateConfigPanel.vue. "
            "UX-04b: the 'next' enum value button must be removed."
        )

    def test_ux04b_this_week_label_removed(self):
        """UX-04b: 'This week' button label must not appear in the source."""
        assert "This week" not in GENERATE_CONFIG_SOURCE, (
            "Found 'This week' in GenerateConfigPanel.vue. "
            "UX-04b: the hardcoded 'This week' label must be removed with the v-btn-toggle."
        )

    def test_ux04b_next_week_label_removed(self):
        """UX-04b: 'Next week' button label must not appear in the source."""
        assert "Next week" not in GENERATE_CONFIG_SOURCE, (
            "Found 'Next week' in GenerateConfigPanel.vue. "
            "UX-04b: the hardcoded 'Next week' label must be removed with the v-btn-toggle."
        )


# ===========================================================================
# UX-04c (D-01..D-06): v-select present with required attributes
# ===========================================================================

class Ux04cVSelectAttributesTests:
    """UX-04c (D-01..D-06): v-select present, full-width, outlined, compact, hide-details, mandatory."""

    def test_ux04c_v_select_appears_exactly_once(self):
        """D-01: Exactly one v-select must be present in the component."""
        count = GENERATE_CONFIG_SOURCE.count("<v-select")
        assert count == 1, (
            f"Expected exactly 1 occurrence of '<v-select', got {count}. "
            "D-01: replace v-btn-toggle with a single full-width v-select."
        )

    def test_ux04c_item_title_title(self):
        """UX-04c: item-title=\"title\" must be present on the v-select."""
        assert 'item-title="title"' in GENERATE_CONFIG_SOURCE, (
            "item-title=\"title\" not found in GenerateConfigPanel.vue. "
            "UX-04c: the v-select must bind item-title to 'title' (the WeekOption.title field)."
        )

    def test_ux04c_item_value_value(self):
        """UX-04c: item-value=\"value\" must be present on the v-select."""
        assert 'item-value="value"' in GENERATE_CONFIG_SOURCE, (
            "item-value=\"value\" not found in GenerateConfigPanel.vue. "
            "UX-04c: the v-select must bind item-value to 'value' (the WeekOption.value ISO string)."
        )

    def test_ux04c_variant_outlined(self):
        """D-02: variant=\"outlined\" must be present (matches panel's dominant form control style)."""
        assert 'variant="outlined"' in GENERATE_CONFIG_SOURCE, (
            "variant=\"outlined\" not found in GenerateConfigPanel.vue. "
            "D-02: v-select must use variant=\"outlined\" to match the v-textarea style."
        )

    def test_ux04c_density_compact(self):
        """D-03: density=\"compact\" must be present on the v-select."""
        assert 'density="compact"' in GENERATE_CONFIG_SOURCE, (
            "density=\"compact\" not found in GenerateConfigPanel.vue. "
            "D-03: v-select must use density=\"compact\" matching all other panel controls."
        )

    def test_ux04c_hide_details(self):
        """D-04: hide-details must be present (matches all other panel controls)."""
        assert "hide-details" in GENERATE_CONFIG_SOURCE, (
            "'hide-details' not found in GenerateConfigPanel.vue. "
            "D-04: v-select must include hide-details matching all other panel controls."
        )

    def test_ux04c_mandatory(self):
        """D-06: mandatory must be present on the v-select (no null/empty state)."""
        assert "mandatory" in GENERATE_CONFIG_SOURCE, (
            "'mandatory' not found in GenerateConfigPanel.vue. "
            "D-06: v-select must be mandatory so no null/empty state is possible."
        )

    def test_ux04c_v_select_has_v_model_selected_week(self):
        """UX-04c: The v-select block must contain v-model=\"selectedWeek\"."""
        v_select_match = re.search(r"<v-select[\s\S]*?/>", GENERATE_CONFIG_SOURCE)
        assert v_select_match, (
            "Could not find a self-closing <v-select ... /> block in GenerateConfigPanel.vue. "
            "UX-04c: the v-select must be present and self-closing."
        )
        v_select_block = v_select_match.group(0)
        assert 'v-model="selectedWeek"' in v_select_block, (
            "v-model=\"selectedWeek\" not found inside the <v-select> block. "
            "UX-04c: the v-select must bind v-model to selectedWeek."
        )

    def test_ux04c_v_select_has_items_week_options(self):
        """UX-04c: The v-select block must contain :items=\"weekOptions\"."""
        v_select_match = re.search(r"<v-select[\s\S]*?/>", GENERATE_CONFIG_SOURCE)
        assert v_select_match, (
            "Could not find a self-closing <v-select ... /> block in GenerateConfigPanel.vue. "
            "UX-04c: the v-select must be present and self-closing."
        )
        v_select_block = v_select_match.group(0)
        assert ':items="weekOptions"' in v_select_block, (
            ':items="weekOptions" not found inside the <v-select> block. '
            "UX-04c: the v-select must bind :items to weekOptions array."
        )

    def test_ux04c_no_label_prop_on_v_select(self):
        """D-05: The v-select must NOT have a built-in label= prop (caption <p> is the visible label)."""
        v_select_match = re.search(r"<v-select[\s\S]*?/>", GENERATE_CONFIG_SOURCE)
        assert v_select_match, (
            "Could not find a self-closing <v-select ... /> block in GenerateConfigPanel.vue."
        )
        v_select_block = v_select_match.group(0)
        assert "label=" not in v_select_block, (
            "Found 'label=' inside the <v-select> block. "
            "D-05: the v-select must not have a built-in label prop — "
            "the <p class=\"text-caption text-medium-emphasis mb-2\"> caption above it serves as the visible label."
        )


# ===========================================================================
# UX-04d: weekOptions 4-option array builder present
# ===========================================================================

class Ux04dWeekOptionsBuilderTests:
    """UX-04d: weekOptions const array built from [0,1,2,3].map(...) must be present."""

    def test_ux04d_week_options_present(self):
        """UX-04d: 'weekOptions' must appear in the source (the options array)."""
        assert "weekOptions" in GENERATE_CONFIG_SOURCE, (
            "'weekOptions' not found in GenerateConfigPanel.vue. "
            "UX-04d: the 4-week options array must be declared as const weekOptions."
        )

    def test_ux04d_four_element_iteration_token(self):
        """UX-04d: [0, 1, 2, 3] or [0,1,2,3] iteration token must appear (4-week builder)."""
        match = re.search(r"\[\s*0\s*,\s*1\s*,\s*2\s*,\s*3\s*\]", GENERATE_CONFIG_SOURCE)
        assert match is not None, (
            "Could not find a [0, 1, 2, 3] four-element array literal in GenerateConfigPanel.vue. "
            "UX-04d: weekOptions must be built by mapping over [0, 1, 2, 3] to produce 4 week options."
        )

    def test_ux04d_week_option_interface_declared(self):
        """UX-04d: 'WeekOption' interface must be declared (title: string, value: string shape)."""
        assert "WeekOption" in GENERATE_CONFIG_SOURCE, (
            "'WeekOption' not found in GenerateConfigPanel.vue. "
            "UX-04d: the WeekOption interface must be declared to type the weekOptions array."
        )


# ===========================================================================
# UX-04e: getMondayOf removed
# ===========================================================================

class Ux04eGetMondayOfRemovedTests:
    """UX-04e: getMondayOf timezone-buggy helper must be entirely removed."""

    def test_ux04e_get_monday_of_removed(self):
        """UX-04e: getMondayOf must not appear anywhere in the source."""
        assert "getMondayOf" not in GENERATE_CONFIG_SOURCE, (
            "Found 'getMondayOf' in GenerateConfigPanel.vue. "
            "UX-04e: the getMondayOf helper uses toISOString() which has a UTC shift bug; "
            "it must be replaced by date-fns startOfWeek({ weekStartsOn: 1 })."
        )


# ===========================================================================
# UX-04f: "this" | "next" enum removed
# ===========================================================================

class Ux04fEnumTypeRemovedTests:
    """UX-04f: 'this' | 'next' enum type for selectedWeek must be entirely removed."""

    def test_ux04f_double_quote_enum_removed(self):
        """UX-04f: '\"this\" | \"next\"' enum type (double-quote style) must not appear."""
        assert '"this" | "next"' not in GENERATE_CONFIG_SOURCE, (
            'Found \'\"this\" | \"next\"\' in GenerateConfigPanel.vue. '
            "UX-04f: the 'this' | 'next' enum type must be removed; selectedWeek is now ref<string>."
        )

    def test_ux04f_single_quote_enum_removed(self):
        """UX-04f: \"'this' | 'next'\" enum type (single-quote style) must not appear."""
        assert "'this' | 'next'" not in GENERATE_CONFIG_SOURCE, (
            "Found \"'this' | 'next'\" in GenerateConfigPanel.vue. "
            "UX-04f: all forms of the 'this' | 'next' enum type must be removed."
        )


# ===========================================================================
# UX-04g: selectedWeek typed as string (or untyped) — no enum ref
# ===========================================================================

class Ux04gSelectedWeekStringRefTests:
    """UX-04g: selectedWeek must be a ref<string> (or ref(isoString)) — not ref<'this'|'next'>."""

    def test_ux04g_enum_ref_type_removed(self):
        """UX-04g: ref<\"this\" | \"next\"> must not appear (old enum ref type)."""
        assert 'ref<"this" | "next">' not in GENERATE_CONFIG_SOURCE, (
            'Found \'ref<"this" | "next">\' in GenerateConfigPanel.vue. '
            "UX-04g: selectedWeek must be typed as ref<string> or ref(isoString), not the old enum type."
        )

    def test_ux04g_selected_week_ref_declaration_present(self):
        """UX-04g: const selectedWeek = ref<...>(...) or ref(...) declaration must be present."""
        match = re.search(
            r"const\s+selectedWeek\s*=\s*ref(?:<[^>]+>)?\(",
            GENERATE_CONFIG_SOURCE,
        )
        assert match is not None, (
            "Could not find 'const selectedWeek = ref<...>(...)' or 'const selectedWeek = ref(...)' "
            "in GenerateConfigPanel.vue. "
            "UX-04g: selectedWeek must be declared as a reactive ref initialized with an ISO date string."
        )


# ===========================================================================
# UX-04h: weekStart computed removed; weekStart: selectedWeek.value in emit
# ===========================================================================

class Ux04hWeekStartComputedRemovedTests:
    """UX-04h: weekStart computed must be removed; emit payload uses selectedWeek.value directly."""

    def test_ux04h_week_start_computed_removed(self):
        """UX-04h: 'const weekStart = computed' must not appear (dead code after migration)."""
        assert "const weekStart = computed" not in GENERATE_CONFIG_SOURCE, (
            "Found 'const weekStart = computed' in GenerateConfigPanel.vue. "
            "UX-04h: the weekStart computed is dead code after migration; selectedWeek IS the ISO string."
        )

    def test_ux04h_week_start_value_removed(self):
        """UX-04h: 'weekStart.value' must not appear (no longer the emit source)."""
        assert "weekStart.value" not in GENERATE_CONFIG_SOURCE, (
            "Found 'weekStart.value' in GenerateConfigPanel.vue. "
            "UX-04h: the emit payload must use selectedWeek.value, not weekStart.value."
        )

    def test_ux04h_emit_uses_selected_week_value(self):
        """UX-04h: 'weekStart: selectedWeek.value' must appear in the emit payload."""
        assert "weekStart: selectedWeek.value" in GENERATE_CONFIG_SOURCE, (
            "'weekStart: selectedWeek.value' not found in GenerateConfigPanel.vue. "
            "UX-04h: onGenerate() must emit weekStart: selectedWeek.value directly "
            "(no intermediate computed)."
        )


# ===========================================================================
# UX-04i: date-fns named import present
# ===========================================================================

class Ux04iDateFnsImportTests:
    """UX-04i: date-fns named import { startOfWeek, addDays, format } must be present."""

    def test_ux04i_start_of_week_imported_from_date_fns(self):
        """UX-04i: startOfWeek must be imported from \"date-fns\" (named import style)."""
        match = re.search(
            r'import\s*\{[^}]*startOfWeek[^}]*\}\s*from\s*"date-fns"',
            GENERATE_CONFIG_SOURCE,
        )
        assert match is not None, (
            "Could not find 'import { ... startOfWeek ... } from \"date-fns\"' in GenerateConfigPanel.vue. "
            "UX-04i: startOfWeek must be imported using named import style from the 'date-fns' package root."
        )

    def test_ux04i_add_days_in_date_fns_import(self):
        """UX-04i: addDays must be in the same date-fns import statement."""
        import_match = re.search(
            r'import\s*\{([^}]*)\}\s*from\s*"date-fns"',
            GENERATE_CONFIG_SOURCE,
        )
        assert import_match, (
            "No 'import { ... } from \"date-fns\"' statement found in GenerateConfigPanel.vue. "
            "UX-04i: addDays must be imported from date-fns."
        )
        import_names = import_match.group(1)
        assert "addDays" in import_names, (
            f"'addDays' not found in the date-fns import statement (found: {import_names.strip()}). "
            "UX-04i: addDays must be imported alongside startOfWeek and format."
        )

    def test_ux04i_format_in_date_fns_import(self):
        """UX-04i: format must be in the same date-fns import statement."""
        import_match = re.search(
            r'import\s*\{([^}]*)\}\s*from\s*"date-fns"',
            GENERATE_CONFIG_SOURCE,
        )
        assert import_match, (
            "No 'import { ... } from \"date-fns\"' statement found in GenerateConfigPanel.vue. "
            "UX-04i: format must be imported from date-fns."
        )
        import_names = import_match.group(1)
        assert "format" in import_names, (
            f"'format' not found in the date-fns import statement (found: {import_names.strip()}). "
            "UX-04i: format must be imported alongside startOfWeek and addDays."
        )

    def test_ux04i_week_starts_on_1_present(self):
        """UX-04i: weekStartsOn: 1 option must be present (ensures Monday-start weeks)."""
        assert "weekStartsOn: 1" in GENERATE_CONFIG_SOURCE, (
            "'weekStartsOn: 1' not found in GenerateConfigPanel.vue. "
            "UX-04i: startOfWeek must be called with { weekStartsOn: 1 } to anchor weeks on Monday."
        )


# ===========================================================================
# UX-04j: Carry-forward fields preserved
# ===========================================================================

class Ux04jCarryForwardFieldsTests:
    """UX-04j: All carry-forward fields (mealTypes, excludedDays, etc.) still present."""

    def test_ux04j_meal_types_const_present(self):
        """UX-04j: const mealTypes must still be present (unchanged carry-forward)."""
        assert "const mealTypes" in GENERATE_CONFIG_SOURCE, (
            "'const mealTypes' not found in GenerateConfigPanel.vue. "
            "UX-04j: mealTypes ref must be preserved as a carry-forward field."
        )

    def test_ux04j_excluded_days_const_present(self):
        """UX-04j: const excludedDays must still be present (unchanged carry-forward)."""
        assert "const excludedDays" in GENERATE_CONFIG_SOURCE, (
            "'const excludedDays' not found in GenerateConfigPanel.vue. "
            "UX-04j: excludedDays ref must be preserved as a carry-forward field."
        )

    def test_ux04j_special_requests_const_present(self):
        """UX-04j: const specialRequests must still be present (unchanged carry-forward)."""
        assert "const specialRequests" in GENERATE_CONFIG_SOURCE, (
            "'const specialRequests' not found in GenerateConfigPanel.vue. "
            "UX-04j: specialRequests ref must be preserved as a carry-forward field."
        )

    def test_ux04j_replace_all_const_present(self):
        """UX-04j: const replaceAll must still be present (unchanged carry-forward)."""
        assert "const replaceAll" in GENERATE_CONFIG_SOURCE, (
            "'const replaceAll' not found in GenerateConfigPanel.vue. "
            "UX-04j: replaceAll ref must be preserved as a carry-forward field."
        )

    def test_ux04j_days_const_present(self):
        """UX-04j: const DAYS must still be present (unchanged carry-forward, moved into script setup)."""
        assert "const DAYS" in GENERATE_CONFIG_SOURCE, (
            "'const DAYS' not found in GenerateConfigPanel.vue. "
            "UX-04j: DAYS constant must be preserved (moved from module-level into <script setup>)."
        )

    def test_ux04j_generate_meal_plan_cta_preserved(self):
        """UX-04j: 'Generate Meal Plan' CTA button text must still be present."""
        assert "Generate Meal Plan" in GENERATE_CONFIG_SOURCE, (
            "'Generate Meal Plan' not found in GenerateConfigPanel.vue. "
            "UX-04j: the primary CTA button text must be preserved unchanged."
        )

    def test_ux04j_cancel_generation_preserved(self):
        """UX-04j: 'Cancel Generation' button text must still be present."""
        assert "Cancel Generation" in GENERATE_CONFIG_SOURCE, (
            "'Cancel Generation' not found in GenerateConfigPanel.vue. "
            "UX-04j: the cancel button text must be preserved unchanged."
        )

    def test_ux04j_d05_caption_class_preserved(self):
        """D-05 (UX-04j): The caption paragraph CSS class must be preserved."""
        assert 'class="text-caption text-medium-emphasis mb-2"' in GENERATE_CONFIG_SOURCE, (
            "The class 'text-caption text-medium-emphasis mb-2' was not found in GenerateConfigPanel.vue. "
            "D-05: the existing <p> caption element above the v-select must be preserved verbatim."
        )

    def test_ux04j_which_week_caption_text_preserved(self):
        """D-05 (UX-04j): 'Which week?' caption text must be preserved."""
        assert "Which week?" in GENERATE_CONFIG_SOURCE, (
            "'Which week?' not found in GenerateConfigPanel.vue. "
            "D-05: the caption text above the week picker must be preserved — "
            "it is the visible label instead of a built-in v-select label prop."
        )


# ===========================================================================
# Smart default (UX-04 Req 4): ISO string logic preserved
# ===========================================================================

class SmartDefaultIsoLogicTests:
    """UX-04 Req 4: Smart default condition and ISO resolution must be present."""

    def test_smart_default_condition_preserved(self):
        """UX-04 Req 4: dayOfWeek >= 1 && dayOfWeek <= 3 condition must appear verbatim."""
        assert "dayOfWeek >= 1 && dayOfWeek <= 3" in GENERATE_CONFIG_SOURCE, (
            "'dayOfWeek >= 1 && dayOfWeek <= 3' not found in GenerateConfigPanel.vue. "
            "UX-04 Req 4: the smart-default condition must be preserved exactly — "
            "Sunday (0) falls into the else branch (next week) by design."
        )

    def test_smart_default_uses_week_options_0_value(self):
        """UX-04 Req 4: weekOptions[0].value must be the Mon-Wed branch result."""
        assert "weekOptions[0].value" in GENERATE_CONFIG_SOURCE, (
            "'weekOptions[0].value' not found in GenerateConfigPanel.vue. "
            "UX-04 Req 4: the Mon-Wed smart default must resolve to weekOptions[0].value "
            "(current week's ISO Monday)."
        )

    def test_smart_default_uses_week_options_1_value(self):
        """UX-04 Req 4: weekOptions[1].value must be the Thu-Sun branch result."""
        assert "weekOptions[1].value" in GENERATE_CONFIG_SOURCE, (
            "'weekOptions[1].value' not found in GenerateConfigPanel.vue. "
            "UX-04 Req 4: the Thu-Sun smart default must resolve to weekOptions[1].value "
            "(next week's ISO Monday)."
        )
