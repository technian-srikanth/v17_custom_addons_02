import logging
import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HRWorkLocation(models.Model):
    _inherit = "hr.work.location"

    wp_location_id = fields.Char(
        string="WordPress Job Location ID",
        tracking=True
    )

    # =====================================================
    # PREPARE PAYLOAD
    # =====================================================

    def _prepare_wp_payload(self):

        self.ensure_one()

        return {
            "name": self.name,
        }

    # =====================================================
    # SYNC TO WORDPRESS
    # =====================================================

    def _sync_location_to_wp(self):

        config = self.env['ir.config_parameter'].sudo()

        username = (
            config.get_param('wp_username') or ""
        ).strip()

        password = (
            config.get_param('wp_password') or ""
        ).strip()

        base_url = (
            config.get_param('wp_worklocation_api') or ""
        ).strip()

        if not base_url:
            raise Exception(
                "WordPress Work Location API URL missing"
            )

        for location in self:

            if not location.name:
                continue

            try:

                data = location._prepare_wp_payload()

                wp_record_exists = False

                # =====================================================
                # VERIFY EXISTING WP ID
                # =====================================================

                if location.wp_location_id:

                    try:

                        response = requests.get(
                            f"{base_url}/{location.wp_location_id}",
                            auth=(username, password),
                            timeout=20
                        )

                        if response.status_code == 200:

                            wp_record_exists = True

                        elif response.status_code == 404:

                            _logger.warning(
                                "WP Location ID %s not found. "
                                "Will create new record.",
                                location.wp_location_id
                            )

                        else:

                            _logger.warning(
                                "Unexpected response while "
                                "checking WP Location ID %s : %s",
                                location.wp_location_id,
                                response.text
                            )

                    except requests.exceptions.RequestException as e:

                        _logger.error(
                            "Failed checking WP location %s : %s",
                            location.wp_location_id,
                            str(e)
                        )

                # =====================================================
                # UPDATE EXISTING
                # =====================================================

                if wp_record_exists:

                    response = requests.put(
                        f"{base_url}/{location.wp_location_id}",
                        json=data,
                        auth=(username, password),
                        timeout=20
                    )

                    if response.status_code not in (200, 201):

                        raise Exception(
                            f"WP Update Error: {response.text}"
                        )

                    _logger.info(
                        "Updated WP Location ID %s",
                        location.wp_location_id
                    )

                # =====================================================
                # CREATE NEW
                # =====================================================

                else:

                    response = requests.post(
                        base_url,
                        json=data,
                        auth=(username, password),
                        timeout=20
                    )

                    if response.status_code not in (200, 201):

                        raise Exception(
                            f"WP Create Error: {response.text}"
                        )

                    result = response.json()

                    created_id = result.get("id")

                    if created_id:

                        location.wp_location_id = str(
                            created_id
                        )

                        _logger.info(
                            "Created new WP Location ID %s",
                            created_id
                        )

                    else:

                        raise Exception(
                            "WP created but no ID returned"
                        )

            except Exception as e:

                _logger.error(
                    "Location sync failed for %s : %s",
                    location.name,
                    str(e)
                )

                raise Exception(
                    f"Location Sync Failed "
                    f"({location.name}) : {str(e)}"
                )

    # =====================================================
    # MANUAL ACTION
    # =====================================================

    def action_publish_to_wp(self):

        self._sync_location_to_wp()

    # =====================================================
    # CRON
    # =====================================================

    def cron_publish_location_to_wp(self):

        locations = self.search([])

        locations._sync_location_to_wp()

    # =====================================================
    # DELETE FROM WORDPRESS
    # =====================================================

    def unlink(self):

        config = self.env['ir.config_parameter'].sudo()

        username = (
            config.get_param('wp_username') or ""
        ).strip()

        password = (
            config.get_param('wp_password') or ""
        ).strip()

        base_url = (
            config.get_param('wp_worklocation_api') or ""
        ).strip()

        for location in self:

            if not location.wp_location_id:
                continue

            try:

                response = requests.delete(
                    f"{base_url}/{location.wp_location_id}",
                    auth=(username, password),
                    params={"force": True},
                    timeout=20
                )

                if response.status_code in (200, 201):

                    _logger.info(
                        "Deleted WP Location ID %s",
                        location.wp_location_id
                    )

                else:

                    _logger.warning(
                        "Failed deleting WP Location "
                        "ID %s : %s",
                        location.wp_location_id,
                        response.text
                    )

            except requests.exceptions.RequestException as e:

                _logger.error(
                    "Delete failed for WP Location "
                    "ID %s : %s",
                    location.wp_location_id,
                    str(e)
                )

        return super(
            HRWorkLocation,
            self
        ).unlink()