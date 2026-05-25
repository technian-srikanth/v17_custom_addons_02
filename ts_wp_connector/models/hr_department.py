import logging
import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    wp_department_id = fields.Char(
        string="WordPress Department ID",
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

    def _sync_department_to_wp(self):

        config = self.env['ir.config_parameter'].sudo()

        username = (
            config.get_param('wp_username') or ""
        ).strip()

        password = (
            config.get_param('wp_password') or ""
        ).strip()

        base_url = (
            config.get_param('wp_department_api') or ""
        ).strip()

        if not base_url:
            raise Exception(
                "WordPress Department API URL missing"
            )

        for department in self:

            if not department.name:
                continue

            try:

                data = department._prepare_wp_payload()

                wp_record_exists = False

                # =====================================================
                # VERIFY EXISTING WP ID
                # =====================================================

                if department.wp_department_id:

                    try:

                        response = requests.get(
                            f"{base_url}/{department.wp_department_id}",
                            auth=(username, password),
                            timeout=20
                        )

                        if response.status_code == 200:

                            wp_record_exists = True

                        elif response.status_code == 404:

                            _logger.warning(
                                "WP Department ID %s not found. "
                                "Will create new record.",
                                department.wp_department_id
                            )

                        else:

                            _logger.warning(
                                "Unexpected response while "
                                "checking WP Department ID %s : %s",
                                department.wp_department_id,
                                response.text
                            )

                    except requests.exceptions.RequestException as e:

                        _logger.error(
                            "Failed checking WP department %s : %s",
                            department.wp_department_id,
                            str(e)
                        )

                # =====================================================
                # UPDATE EXISTING
                # =====================================================

                if wp_record_exists:

                    response = requests.put(
                        f"{base_url}/{department.wp_department_id}",
                        json=data,
                        auth=(username, password),
                        timeout=20
                    )

                    if response.status_code not in (200, 201):

                        raise Exception(
                            f"WP Update Error: {response.text}"
                        )

                    _logger.info(
                        "Updated WP Department ID %s",
                        department.wp_department_id
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

                        department.wp_department_id = str(
                            created_id
                        )

                        _logger.info(
                            "Created new WP Department ID %s",
                            created_id
                        )

                    else:

                        raise Exception(
                            "WP created but no ID returned"
                        )

            except Exception as e:

                _logger.error(
                    "Department sync failed for %s : %s",
                    department.name,
                    str(e)
                )

                raise Exception(
                    f"Department Sync Failed "
                    f"({department.name}) : {str(e)}"
                )

    # =====================================================
    # MANUAL ACTION
    # =====================================================

    def action_publish_to_wp(self):

        self._sync_department_to_wp()

    # =====================================================
    # CRON
    # =====================================================

    def cron_publish_department_to_wp(self):

        departments = self.search([])

        departments._sync_department_to_wp()

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
            config.get_param('wp_department_api') or ""
        ).strip()

        for department in self:

            if not department.wp_department_id:
                continue

            try:

                response = requests.delete(
                    f"{base_url}/{department.wp_department_id}",
                    auth=(username, password),
                    params={"force": True},
                    timeout=20
                )

                if response.status_code in (200, 201):

                    _logger.info(
                        "Deleted WP Department ID %s",
                        department.wp_department_id
                    )

                else:

                    _logger.warning(
                        "Failed deleting WP Department "
                        "ID %s : %s",
                        department.wp_department_id,
                        response.text
                    )

            except requests.exceptions.RequestException as e:

                _logger.error(
                    "Delete failed for WP Department "
                    "ID %s : %s",
                    department.wp_department_id,
                    str(e)
                )

        return super(HrDepartment, self).unlink()