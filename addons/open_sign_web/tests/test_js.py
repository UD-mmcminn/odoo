# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.web.tests.test_js import unit_test_error_checker


@odoo.tests.tagged("post_install", "-at_install")
class OpenSignWebSuite(odoo.tests.HttpCase):
    @odoo.tests.no_retry
    def test_open_sign_web_unit_desktop(self):
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&tag=open_sign_web",
            "",
            "",
            login="admin",
            timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )

    def test_open_sign_web_assets_registered(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_unit_tests")
        test_files = [
            file.get("filename")
            for file in bundle.files
            if "open_sign_web/static/tests/" in file.get("filename", "")
            and file.get("filename", "").endswith(".test.js")
        ]
        self.assertTrue(
            test_files,
            "Expected open_sign_web frontend tests in web.assets_unit_tests bundle.",
        )
