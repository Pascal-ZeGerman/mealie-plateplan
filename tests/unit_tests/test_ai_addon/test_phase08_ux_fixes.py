"""
Phase 08-01 UX Fixes — Structural/behavioral source-analysis tests.

These tests read the Vue source files directly and assert the presence
(or absence) of specific structural patterns required by decisions
D-01 through D-10. Static source analysis is the correct approach here
because: (a) Docker is not guaranteed up in CI, (b) no @vue/test-utils
is installed, and (c) the behaviors being verified are structural
template/script properties, not runtime dynamic behavior.

Gaps covered:
  GAP-1 (UX-01 / D-10): Nav link "View in Mealie Calendar" -> /household/mealplan/planner
  GAP-2 (UX-02 / D-01-D-05): Lock icon in slot header row, visible without hover
  GAP-3 (UX-03 / D-06-D-09): Optimistic lock toggle + rollback + error snackbar
"""
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Source file paths (absolute, relative to this repo layout)
# ---------------------------------------------------------------------------
MEALIE_ROOT = Path(__file__).parents[3]  # mealie/
PLAN_VUE = MEALIE_ROOT / "frontend/pages/ai-meal-planner/plan.vue"
SLOT_CARD_VUE = MEALIE_ROOT / "frontend/components/ai-meal-planner/MealSlotCard.vue"


def _read(path: Path) -> str:
    assert path.exists(), f"Implementation file not found: {path}"
    return path.read_text(encoding="utf-8")


# Load once at module level (fast, pure I/O)
PLAN_SOURCE = _read(PLAN_VUE)
SLOT_CARD_SOURCE = _read(SLOT_CARD_VUE)


# ===========================================================================
# GAP-1: UX-01 / D-10 — "View in Mealie Calendar" nav link target
# ===========================================================================

class Gap1NavLinkTests:
    """GAP-1: Nav link 'View in Mealie Calendar' must target /household/mealplan/planner."""

    def test_corrected_route_appears_exactly_once(self):
        """D-10: The corrected route /household/mealplan/planner must be present."""
        count = PLAN_SOURCE.count('to="/household/mealplan/planner"')
        assert count == 1, (
            f"Expected exactly 1 occurrence of to=\"/household/mealplan/planner\", got {count}. "
            "D-10 requires the nav link to use the corrected Mealie calendar route."
        )

    def test_broken_route_meal_plans_is_gone(self):
        """D-10: The old broken route /meal-plans must no longer appear in plan.vue."""
        count = PLAN_SOURCE.count('to="/meal-plans"')
        assert count == 0, (
            f"Found {count} occurrence(s) of to=\"/meal-plans\" — the broken route was not removed. "
            "D-10 requires replacing this with /household/mealplan/planner."
        )

    def test_label_text_view_in_mealie_calendar_preserved(self):
        """D-10: Label text 'View in Mealie Calendar' must still appear exactly once."""
        count = PLAN_SOURCE.count("View in Mealie Calendar")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'View in Mealie Calendar', got {count}. "
            "The nav link label must be preserved unchanged."
        )

    def test_nav_link_gated_by_committed_state(self):
        """D-10: Nav link must only be visible when planState === 'committed'."""
        has_guard = (
            "v-if=\"planState === 'committed'\"" in PLAN_SOURCE
            or "v-if='planState === \"committed\"'" in PLAN_SOURCE
        )
        assert has_guard, (
            "Could not find v-if=\"planState === 'committed'\" guard in plan.vue. "
            "The nav link must be gated to the committed state only."
        )

    def test_nav_link_css_classes_preserved(self):
        """D-10: CSS classes text-caption text-decoration-none text-primary mr-2 must be intact."""
        assert "text-caption text-decoration-none text-primary mr-2" in PLAN_SOURCE, (
            "CSS classes on the NuxtLink were modified. "
            "Expected: 'text-caption text-decoration-none text-primary mr-2'."
        )


# ===========================================================================
# GAP-2: UX-02 / D-01-D-05 — Lock icon in slot header row, visible without hover
# ===========================================================================

class Gap2LockIconHeaderRowTests:
    """GAP-2: Lock icon must be a clickable v-btn in the header row, never in .slot-actions."""

    def test_d02_d03_unlock_aria_label_appears_exactly_once(self):
        """D-02/D-03: 'Unlock this meal' aria-label must appear exactly once (header v-btn only)."""
        count = SLOT_CARD_SOURCE.count("Unlock this meal")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'Unlock this meal', got {count}. "
            "D-02: the aria-label must be on the header v-btn. D-03: the hover-only .slot-actions "
            "version must have been removed."
        )

    def test_d02_d04_lock_aria_label_appears_exactly_once(self):
        """D-02/D-04: 'Lock this meal' aria-label must appear exactly once (header v-btn only)."""
        count = SLOT_CARD_SOURCE.count("Lock this meal — it will survive regeneration")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'Lock this meal — it will survive regeneration', got {count}. "
            "D-04: the header v-btn must be the sole source."
        )

    def test_d03_unlock_emit_appears_exactly_once(self):
        """D-03: $emit('unlock', slot) must appear exactly once — only in the header, not in .slot-actions."""
        # Match the emit pattern with possible whitespace variations
        matches = re.findall(r"\$emit\('unlock',\s*slot\)", SLOT_CARD_SOURCE)
        assert len(matches) == 1, (
            f"Expected exactly 1 occurrence of $emit('unlock', slot), got {len(matches)}. "
            "D-03: the hover-only unlock button in .slot-actions must be removed."
        )

    def test_d04_lock_emit_appears_exactly_once(self):
        """D-04: $emit('lock', slot) must appear exactly once — only in the header, not in .slot-actions."""
        matches = re.findall(r"\$emit\('lock',\s*slot\)", SLOT_CARD_SOURCE)
        assert len(matches) == 1, (
            f"Expected exactly 1 occurrence of $emit('lock', slot), got {len(matches)}. "
            "D-04: the hover-only lock button in .slot-actions must be removed."
        )

    def test_d03_locked_slot_branch_has_no_slot_actions_div(self):
        """D-03: The locked-slot branch must not contain a .slot-actions div (it was removed).

        After D-03, the locked-slot branch lost its .slot-actions div.
        Only the normal-slot branch and the text-slot branch retain .slot-actions.
        Total count in the file must be exactly 2 (not 3).
        """
        count = SLOT_CARD_SOURCE.count('class="d-flex justify-end slot-actions"')
        assert count == 2, (
            f"Expected exactly 2 occurrences of slot-actions (normal-slot + text-slot), got {count}. "
            "D-03: the locked-slot branch's .slot-actions div must be removed."
        )

    def test_d01_unlock_btn_is_in_header_row_not_slot_actions(self):
        """D-01: The 'Unlock this meal' v-btn must be inside the header row div, before any .slot-actions."""
        # Extract the locked-slot branch (v-else-if="slot.isLocked" ... closing </v-card>)
        locked_branch_match = re.search(
            r'v-else-if="slot\.isLocked"[\s\S]*?</v-card>',
            SLOT_CARD_SOURCE,
        )
        assert locked_branch_match, "Could not find the locked-slot branch (v-else-if=\"slot.isLocked\") in MealSlotCard.vue"
        locked_branch = locked_branch_match.group(0)

        header_div_idx = locked_branch.find('class="d-flex align-center justify-space-between mb-1"')
        unlock_idx = locked_branch.find("Unlock this meal")
        slot_actions_idx = locked_branch.find("slot-actions")

        assert header_div_idx >= 0, "Header row div not found in the locked-slot branch."
        assert unlock_idx > header_div_idx, (
            "The 'Unlock this meal' aria-label does not appear after the header row div in the locked-slot branch. "
            "D-01: the unlock v-btn must be inside the header row."
        )
        # slot-actions must either be absent or appear after the unlock btn (which means the btn is in header, not actions)
        if slot_actions_idx >= 0:
            assert unlock_idx < slot_actions_idx, (
                "The 'Unlock this meal' button appears inside .slot-actions, not before it. "
                "D-01: it must be in the header row."
            )

    def test_d01_lock_btn_is_in_header_row_before_slot_actions(self):
        """D-01: The 'Lock this meal' v-btn must be inside the header row div, before .slot-actions."""
        # Extract the normal-slot branch (v-else ... closing </v-card></template>)
        normal_branch_match = re.search(
            r'<!-- Normal recipe slot -->[\s\S]*?</v-card>\s*</template>',
            SLOT_CARD_SOURCE,
        )
        assert normal_branch_match, "Could not find the normal-slot branch (<!-- Normal recipe slot -->) in MealSlotCard.vue"
        normal_branch = normal_branch_match.group(0)

        header_div_idx = normal_branch.find('class="d-flex align-center justify-space-between mb-1"')
        lock_label_idx = normal_branch.find("Lock this meal — it will survive regeneration")
        slot_actions_idx = normal_branch.find("slot-actions")

        assert header_div_idx >= 0, "Header row div not found in the normal-slot branch."
        assert lock_label_idx > header_div_idx, (
            "The 'Lock this meal' aria-label does not appear after the header row div in the normal-slot branch. "
            "D-01: the lock v-btn must be inside the header row."
        )
        assert slot_actions_idx > lock_label_idx, (
            "The 'Lock this meal' button appears inside or after .slot-actions. "
            "D-01: it must be in the header row, which comes before .slot-actions."
        )

    def test_d05_unlock_btn_in_locked_branch_has_show_actions_gate(self):
        """D-05: The header unlock v-btn must be gated by v-if='showActions'."""
        locked_branch_match = re.search(
            r'v-else-if="slot\.isLocked"[\s\S]*?</v-card>',
            SLOT_CARD_SOURCE,
        )
        assert locked_branch_match, "Could not find the locked-slot branch."
        locked_branch = locked_branch_match.group(0)
        assert 'v-if="showActions"' in locked_branch, (
            "The locked-slot header v-btn is missing v-if=\"showActions\" gate. "
            "D-05: the always-visible header button must still respect the showActions prop."
        )

    def test_d05_lock_btn_in_normal_branch_has_show_actions_gate(self):
        """D-05: The header lock v-btn in the normal slot must be gated by v-if='showActions'."""
        normal_branch_match = re.search(
            r'<!-- Normal recipe slot -->[\s\S]*?</v-card>\s*</template>',
            SLOT_CARD_SOURCE,
        )
        assert normal_branch_match, "Could not find the normal-slot branch."
        normal_branch = normal_branch_match.group(0)
        # The header lock btn should have v-if="showActions" before the slot-actions div
        # Find v-if="showActions" that appears before slot-actions
        show_actions_indices = [m.start() for m in re.finditer(r'v-if="showActions"', normal_branch)]
        slot_actions_idx = normal_branch.find("slot-actions")
        header_div_idx = normal_branch.find('class="d-flex align-center justify-space-between mb-1"')

        # At least one v-if="showActions" must appear in the header section (before slot-actions)
        header_show_actions = [i for i in show_actions_indices if header_div_idx < i < slot_actions_idx]
        assert len(header_show_actions) >= 1, (
            "No v-if=\"showActions\" found in the normal-slot header row (before .slot-actions). "
            "D-05: the lock v-btn in the normal-slot header must be gated by showActions."
        )

    def test_d04_slot_actions_in_normal_branch_has_no_lock_emit(self):
        """D-04: The remaining .slot-actions div in the normal-slot must NOT contain a lock/unlock emit."""
        normal_branch_match = re.search(
            r'<!-- Normal recipe slot -->[\s\S]*?</v-card>\s*</template>',
            SLOT_CARD_SOURCE,
        )
        assert normal_branch_match, "Could not find the normal-slot branch."
        normal_branch = normal_branch_match.group(0)

        # Extract the .slot-actions block
        slot_actions_match = re.search(
            r'class="d-flex justify-end slot-actions"[\s\S]*?</div>',
            normal_branch,
        )
        if slot_actions_match:
            slot_actions_block = slot_actions_match.group(0)
            assert "$emit('lock'" not in slot_actions_block, (
                "Found $emit('lock') inside .slot-actions of the normal-slot branch. "
                "D-04: the lock button must be removed from .slot-actions."
            )
            assert "$emit('unlock'" not in slot_actions_block, (
                "Found $emit('unlock') inside .slot-actions of the normal-slot branch. "
                "D-04: no unlock button should be in the normal-slot .slot-actions."
            )

    def test_d04_slot_actions_swap_and_remove_are_still_present(self):
        """D-04: The normal-slot .slot-actions must still contain the swap and remove buttons."""
        normal_branch_match = re.search(
            r'<!-- Normal recipe slot -->[\s\S]*?</v-card>\s*</template>',
            SLOT_CARD_SOURCE,
        )
        assert normal_branch_match, "Could not find the normal-slot branch."
        normal_branch = normal_branch_match.group(0)

        slot_actions_match = re.search(
            r'class="d-flex justify-end slot-actions"[\s\S]*?</div>',
            normal_branch,
        )
        assert slot_actions_match, "No .slot-actions div found in the normal-slot branch."
        slot_actions_block = slot_actions_match.group(0)

        assert "$emit('swap'" in slot_actions_block, (
            "The swap v-btn is missing from .slot-actions in the normal-slot branch. "
            "D-04 requires swap and remove to remain."
        )
        assert "$emit('remove'" in slot_actions_block, (
            "The remove v-btn is missing from .slot-actions in the normal-slot branch. "
            "D-04 requires swap and remove to remain."
        )


# ===========================================================================
# GAP-3: UX-03 / D-06-D-09 — Optimistic lock toggle + rollback + error snackbar
# ===========================================================================

class Gap3OptimisticLockToggleTests:
    """GAP-3: handleLockToggle must be async, optimistic, with rollback and error snackbar."""

    def test_d06_handle_lock_toggle_is_async(self):
        """D-06: handleLockToggle must be declared as an async function."""
        count = len(re.findall(r"async function handleLockToggle", PLAN_SOURCE))
        assert count == 1, (
            f"Expected exactly 1 'async function handleLockToggle', got {count}. "
            "D-06: the function must be async to support the await API call."
        )

    def test_d06_prev_locked_captured_before_flip(self):
        """D-06: prevLocked must be captured from slots.value[idx].isLocked before the optimistic flip."""
        count = len(re.findall(
            r"const prevLocked\s*=\s*slots\.value\[idx\]\.isLocked",
            PLAN_SOURCE,
        ))
        assert count == 1, (
            f"Expected exactly 1 'const prevLocked = slots.value[idx].isLocked', got {count}. "
            "D-06: prevLocked must be captured before the optimistic flip to enable rollback."
        )

    def test_d06_optimistic_flip_before_await(self):
        """D-06: The optimistic flip (isLocked: !prevLocked) must occur BEFORE the await API call."""
        fn_start = PLAN_SOURCE.find("async function handleLockToggle")
        assert fn_start >= 0, "handleLockToggle function not found in plan.vue."

        prev_locked_assign_idx = PLAN_SOURCE.find(
            "const prevLocked = slots.value[idx].isLocked", fn_start
        )
        assert prev_locked_assign_idx > fn_start, "prevLocked assignment not found in handleLockToggle."

        # Find the first occurrence of isLocked: !prevLocked after the assignment
        optimistic_flip_idx = PLAN_SOURCE.find("isLocked: !prevLocked", prev_locked_assign_idx)
        assert optimistic_flip_idx > prev_locked_assign_idx, (
            "Optimistic flip 'isLocked: !prevLocked' not found after prevLocked assignment. "
            "D-06: the UI must update before the API call."
        )

        # Find the await API call
        await_idx = PLAN_SOURCE.find("await api.aiAddon.updateMetadata", fn_start)
        assert await_idx > fn_start, "await api.aiAddon.updateMetadata not found in handleLockToggle."

        assert optimistic_flip_idx < await_idx, (
            f"Optimistic flip at position {optimistic_flip_idx} comes AFTER await at {await_idx}. "
            "D-06: the flip must occur BEFORE the API call for optimistic UI behavior."
        )

    def test_d07_catch_block_restores_prev_locked(self):
        """D-07: The catch block must restore isLocked: prevLocked (rollback on API failure)."""
        # isLocked: prevLocked must appear in the source (rollback assignment)
        rollback_count = len(re.findall(r"isLocked:\s*prevLocked", PLAN_SOURCE))
        assert rollback_count >= 1, (
            f"Expected at least 1 occurrence of 'isLocked: prevLocked', got {rollback_count}. "
            "D-07: the catch block must roll back the optimistic flip on API failure."
        )

        # Verify it's inside the catch block
        fn_start = PLAN_SOURCE.find("async function handleLockToggle")
        catch_idx = PLAN_SOURCE.find("catch (_e)", fn_start)
        assert catch_idx > fn_start, "No catch block found inside handleLockToggle."

        rollback_in_catch_idx = PLAN_SOURCE.find("isLocked: prevLocked", catch_idx)
        assert rollback_in_catch_idx > catch_idx, (
            "'isLocked: prevLocked' rollback not found inside the catch block. "
            "D-07: rollback must happen specifically on API failure."
        )

    def test_d07_lock_error_set_in_catch_block(self):
        """D-07: lockError.value = true must be set in the catch block (not silent swallow)."""
        # Must appear exactly once in the whole file
        count = len(re.findall(r"lockError\.value\s*=\s*true", PLAN_SOURCE))
        assert count == 1, (
            f"Expected exactly 1 'lockError.value = true', got {count}. "
            "D-07: the error must be surfaced to the user, not swallowed silently."
        )

        # Must be inside the catch block
        fn_start = PLAN_SOURCE.find("async function handleLockToggle")
        catch_idx = PLAN_SOURCE.find("catch (_e)", fn_start)
        lock_error_set_idx = PLAN_SOURCE.find("lockError.value = true", catch_idx)
        assert lock_error_set_idx > catch_idx, (
            "lockError.value = true not found inside the catch block. "
            "D-07: must set lockError in the catch to trigger the error snackbar."
        )

    def test_d07_prev_locked_appears_at_least_3_times(self):
        """D-07: prevLocked must appear >= 3 times (assign, optimistic flip, rollback)."""
        count = len(re.findall(r"prevLocked", PLAN_SOURCE))
        assert count >= 3, (
            f"Expected at least 3 occurrences of 'prevLocked', got {count}. "
            "D-06 + D-07: need assignment (1), optimistic flip (2), rollback (3)."
        )

    def test_d08_error_snackbar_exact_copy_text(self):
        """D-08: Error snackbar text must be exactly 'Could not update lock — try again' (em dash, no period)."""
        count = PLAN_SOURCE.count("Could not update lock — try again")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 'Could not update lock — try again', got {count}. "
            "D-08: the exact copy with em dash (not hyphen) and no trailing period is required."
        )

    def test_d09_lock_error_snackbar_v_model(self):
        """D-09: Error snackbar must use v-model='lockError'."""
        count = len(re.findall(r'v-model="lockError"', PLAN_SOURCE))
        assert count == 1, (
            f"Expected exactly 1 'v-model=\"lockError\"', got {count}. "
            "D-09: the lockError snackbar must bind to the lockError ref."
        )

    def test_d09_lock_error_snackbar_has_color_error(self):
        """D-09: The lockError snackbar must use color='error'."""
        snackbar_match = re.search(
            r'v-model="lockError"[\s\S]*?</v-snackbar>',
            PLAN_SOURCE,
        )
        assert snackbar_match, "lockError v-snackbar block not found in plan.vue."
        snackbar_block = snackbar_match.group(0)
        assert 'color="error"' in snackbar_block, (
            "lockError snackbar is missing color=\"error\". "
            "D-09: must match the rating error snackbar pattern."
        )

    def test_d09_lock_error_snackbar_has_timeout_4000(self):
        """D-09: The lockError snackbar must use :timeout='4000'."""
        snackbar_match = re.search(
            r'v-model="lockError"[\s\S]*?</v-snackbar>',
            PLAN_SOURCE,
        )
        assert snackbar_match, "lockError v-snackbar block not found in plan.vue."
        snackbar_block = snackbar_match.group(0)
        assert ':timeout="4000"' in snackbar_block, (
            "lockError snackbar is missing :timeout=\"4000\". "
            "D-09: 4-second timeout required to match the existing error snackbar pattern."
        )

    def test_d09_lock_error_ref_declared_as_ref_false(self):
        """D-09: lockError must be declared as ref(false) in the script setup block."""
        count = len(re.findall(r"const lockError\s*=\s*ref\(false\)", PLAN_SOURCE))
        assert count == 1, (
            f"Expected exactly 1 'const lockError = ref(false)', got {count}. "
            "D-09: lockError must be a reactive boolean ref bound to the snackbar v-model."
        )

    def test_d09_lock_error_exposed_in_return_object(self):
        """D-09: lockError must be in the setup() return object (accessible from template)."""
        return_block_match = re.search(r"return \{[\s\S]*?\};", PLAN_SOURCE)
        assert return_block_match, "Could not find 'return { ... };' block in plan.vue setup()."
        return_block = return_block_match.group(0)
        assert "lockError" in return_block, (
            "lockError not found in the setup() return object. "
            "D-09: it must be returned so the template v-model can bind to it."
        )

    def test_d09_lock_error_snackbar_has_no_location_prop(self):
        """D-09: lockError snackbar must NOT have a 'location' prop (matches success snackbar pattern)."""
        snackbar_match = re.search(
            r'v-model="lockError"[\s\S]*?</v-snackbar>',
            PLAN_SOURCE,
        )
        assert snackbar_match, "lockError v-snackbar block not found in plan.vue."
        snackbar_block = snackbar_match.group(0)
        assert "location=" not in snackbar_block, (
            "lockError snackbar has an unexpected 'location=' prop. "
            "D-09: should match the success snackbar which has no location (default bottom-center)."
        )

    def test_success_snackbar_unchanged(self):
        """Regression: The existing success snackbar must be unchanged."""
        assert 'v-model="showSuccessSnackbar"' in PLAN_SOURCE, (
            "showSuccessSnackbar snackbar v-model missing — success snackbar was modified."
        )
        assert "Your meal plan has been saved to Mealie." in PLAN_SOURCE, (
            "Success snackbar text changed — unexpected regression."
        )

    def test_lock_error_snackbar_appears_after_success_snackbar(self):
        """D-09: lockError snackbar must be added AFTER the success snackbar (template order)."""
        success_idx = PLAN_SOURCE.find('v-model="showSuccessSnackbar"')
        lock_error_idx = PLAN_SOURCE.find('v-model="lockError"')
        assert success_idx >= 0, "showSuccessSnackbar snackbar not found."
        assert lock_error_idx >= 0, "lockError snackbar not found."
        assert lock_error_idx > success_idx, (
            "lockError snackbar appears BEFORE the success snackbar in the template. "
            "D-09: the new snackbar must be added after the existing one."
        )
