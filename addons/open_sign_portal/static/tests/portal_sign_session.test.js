import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { startInteraction } from "@web/../tests/public/helpers";
import { rpc } from "@web/core/network/rpc";

import { OpenSignPortalSession } from "@open_sign_portal/interactions/portal_sign_session";

describe.current.tags("headless", "open_sign_portal");

function makeSessionHtml() {
    return `
        <div
            class="o_open_sign_session"
            data-signer-id="42"
            data-submit-url="/my/sign/42/submit"
            data-decline-url="/my/sign/42/decline"
            data-request-revision="3"
            data-access-token="token-123"
            data-consent-hash="consent-hash-123"
        >
            <div class="o_open_sign_error d-none"></div>
            <div class="o_open_sign_success d-none"></div>
            <div class="o_open_sign_request_status"></div>
            <input class="o_open_sign_consent" type="checkbox" checked />
            <textarea class="o_open_sign_decline_reason">Decline reason</textarea>
            <div class="o_open_sign_field" data-field-id="10" data-field-type="text">
                <input class="o_open_sign_input" value="Field value" />
            </div>
        </div>
    `;
}

async function startPortalInteraction() {
    const { core } = await startInteraction(OpenSignPortalSession, makeSessionHtml());
    return core.interactions[0].interaction;
}

beforeEach(() => {
    window.sessionStorage.clear();
});

test("submit keeps pending key on request_locked", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "request_locked", message: "Locked" }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(key);
});

test("decline keeps pending key on request_locked", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("decline");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "request_locked", message: "Locked" }),
    });

    await interaction.onClickDecline();

    expect(interaction._getPendingIdempotencyKey("decline")).toBe(key);
});

test("pending key is cleared on success", async () => {
    const interaction = await startPortalInteraction();
    interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: true, request_revision: 4 }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(false);
});

test("pending key is cleared on definitive json error", async () => {
    const interaction = await startPortalInteraction();
    interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => ({ ok: false, error_code: "validation_error", message: "Invalid" }),
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(false);
});

test("pending key is preserved on transport failure", async () => {
    const interaction = await startPortalInteraction();
    const key = interaction._getOrCreatePendingIdempotencyKey("submit");
    patchWithCleanup(rpc, {
        _rpc: async () => {
            throw new Error("network failure");
        },
    });

    await interaction.onClickSubmit();

    expect(interaction._getPendingIdempotencyKey("submit")).toBe(key);
});
