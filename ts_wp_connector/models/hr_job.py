import logging
import requests

from bs4 import BeautifulSoup
from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrJob(models.Model):
    _inherit = "hr.job"

    website_job_id = fields.Char(
        string="WordPress Job ID",
        tracking=True
    )

    work_location_id = fields.Many2many(
        "hr.work.location",
        string="Work Location"
    )

    role_line_ids = fields.One2many(
        "hr.job.line",
        inverse_name="job_id",
        string="Tasks and Responsibilities"
    )

    job_requirement_ids = fields.One2many(
        "hr.job.requirement.line",
        inverse_name="job_id",
        string="Skills and Qualifications"
    )

    # =====================================================
    # PREPARE WP PAYLOAD
    # =====================================================

    def _prepare_wp_payload(self):

        self.ensure_one()

        raw_desc = self.description or ""

        soup = BeautifulSoup(
            raw_desc,
            "html.parser"
        )

        # remove unwanted data-* attributes
        for tag in soup.find_all(True):

            for attr in list(tag.attrs):

                if attr.startswith("data-"):
                    del tag.attrs[attr]

        # ensure valid paragraph structure
        if not soup.find("p"):

            lines = [
                line.strip()
                for line in raw_desc.split("\n")
                if line.strip()
            ]

            html_content = "".join(
                f"<p>{line}</p>"
                for line in lines
            )

        else:
            html_content = str(soup)

        wp_status = (
            "publish"
            if self.website_published
            else "draft"
        )

        data = {
            "title": self.name,
            "content": html_content,
            "status": wp_status,
        }

        acf_data = {}

        # =====================================================
        # TASKS
        # =====================================================

        if self.role_line_ids:

            acf_data["job_tasks_and_responsibilities"] = [
                {
                    "task_and_responsibility":
                        line.roles_id.name
                }
                for line in self.role_line_ids
                if line.roles_id
            ]

        # =====================================================
        # REQUIREMENTS
        # =====================================================

        if self.job_requirement_ids:

            acf_data["job_skills_and_qualifications"] = [
                {
                    "skill_and_qualification":
                        line.requirement_id.name
                }
                for line in self.job_requirement_ids
                if line.requirement_id
            ]

        # =====================================================
        # OPENINGS
        # =====================================================

        if self.no_of_recruitment:

            acf_data["job_openings"] = str(
                self.no_of_recruitment
            )

        if acf_data:
            data["acf"] = acf_data

        # =====================================================
        # DEPARTMENT
        # =====================================================

        if (
            self.department_id
            and self.department_id.wp_department_id
        ):

            try:

                data["job-type"] = [
                    int(self.department_id.wp_department_id)
                ]

            except Exception:

                _logger.warning(
                    "Invalid wp_department_id "
                    "for job %s",
                    self.name
                )

        # =====================================================
        # LOCATIONS
        # =====================================================

        if self.work_location_id:

            location_ids = []

            for location in self.work_location_id:

                if location.wp_location_id:

                    try:

                        location_ids.append(
                            int(location.wp_location_id)
                        )

                    except Exception:

                        _logger.warning(
                            "Invalid wp_location_id: %s",
                            location.wp_location_id
                        )

            if location_ids:
                data["job-location"] = location_ids

        return data

    # =====================================================
    # SYNC TO WORDPRESS
    # =====================================================

    def _sync_jobs_to_wp(self):

        config = self.env[
            "ir.config_parameter"
        ].sudo()

        username = (
            config.get_param("wp_username") or ""
        ).strip()

        password = (
            config.get_param("wp_password") or ""
        ).strip()

        base_url = (
            config.get_param("wp_job_api") or ""
        ).strip()

        if not base_url:

            raise Exception(
                "WordPress API URL missing"
            )

        for job in self:

            if not job.name:
                continue

            try:

                # =====================================================
                # AUTO SYNC DEPARTMENT
                # =====================================================

                if job.department_id:

                    job.department_id._sync_department_to_wp()

                # =====================================================
                # AUTO SYNC WORK LOCATIONS
                # =====================================================

                if job.work_location_id:

                    job.work_location_id._sync_location_to_wp()

                # =====================================================
                # PREPARE JOB DATA
                # =====================================================

                data = job._prepare_wp_payload()

                wp_record_exists = False

                # =====================================================
                # VERIFY EXISTING WP ID
                # =====================================================

                if job.website_job_id:

                    try:

                        response = requests.get(
                            f"{base_url}/{job.website_job_id}",
                            auth=(username, password),
                            timeout=20
                        )

                        if response.status_code == 200:

                            wp_record_exists = True

                        elif response.status_code == 404:

                            _logger.warning(
                                "WP Job ID %s not found. "
                                "Will create new record.",
                                job.website_job_id
                            )

                        else:

                            _logger.warning(
                                "Unexpected response while "
                                "checking WP Job ID %s : %s",
                                job.website_job_id,
                                response.text
                            )

                    except requests.exceptions.RequestException as e:

                        _logger.error(
                            "Failed checking WP job %s : %s",
                            job.website_job_id,
                            str(e)
                        )

                # =====================================================
                # UPDATE EXISTING
                # =====================================================

                if wp_record_exists:

                    response = requests.put(
                        f"{base_url}/{job.website_job_id}",
                        json=data,
                        auth=(username, password),
                        timeout=20
                    )

                    if response.status_code not in (200, 201):

                        raise Exception(
                            f"WP Update Error: "
                            f"{response.text}"
                        )

                    _logger.info(
                        "Updated WP Job ID %s",
                        job.website_job_id
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
                            f"WP Create Error: "
                            f"{response.text}"
                        )

                    result = response.json()

                    created_id = result.get("id")

                    if created_id:

                        job.website_job_id = str(
                            created_id
                        )

                        _logger.info(
                            "Created new WP Job ID %s",
                            created_id
                        )

                    else:

                        raise Exception(
                            "WP created but "
                            "no ID returned"
                        )

            except Exception as e:

                _logger.error(
                    "Job sync failed for %s : %s",
                    job.name,
                    str(e)
                )

                raise Exception(
                    f"Job Sync Failed "
                    f"({job.name}) : {str(e)}"
                )

    # =====================================================
    # MANUAL ACTION
    # =====================================================

    def action_publish_to_wp(self):

        self._sync_jobs_to_wp()

    # =====================================================
    # CRON
    # =====================================================

    def cron_publish_jobs_to_wp(self):

        jobs = self.search([])

        jobs._sync_jobs_to_wp()

    # =====================================================
    # DELETE FROM WORDPRESS
    # =====================================================

    def unlink(self):

        config = self.env[
            "ir.config_parameter"
        ].sudo()

        username = (
            config.get_param("wp_username") or ""
        ).strip()

        password = (
            config.get_param("wp_password") or ""
        ).strip()

        base_url = (
            config.get_param("wp_job_api") or ""
        ).strip()

        for job in self:

            if not job.website_job_id:
                continue

            try:

                response = requests.delete(
                    f"{base_url}/{job.website_job_id}",
                    auth=(username, password),
                    params={"force": False},
                    timeout=20
                )

                if response.status_code == 200:

                    _logger.info(
                        "Deleted WP Job ID %s",
                        job.website_job_id
                    )

                else:

                    _logger.warning(
                        "Failed deleting WP Job ID %s : %s",
                        job.website_job_id,
                        response.text
                    )

            except requests.exceptions.RequestException as e:

                _logger.error(
                    "Delete failed for WP Job ID %s : %s",
                    job.website_job_id,
                    str(e)
                )

        return super(
            HrJob,
            self
        ).unlink()


# =====================================================
# ROLE
# =====================================================

class HrRole(models.Model):

    _name = "hr.role"

    name = fields.Char()


# =====================================================
# JOB LINE
# =====================================================

class HrJobLine(models.Model):

    _name = "hr.job.line"

    name = fields.Char()

    job_id = fields.Many2one(
        "hr.job"
    )

    roles_id = fields.Many2one(
        "hr.role"
    )


# =====================================================
# REQUIREMENT
# =====================================================

class HrJobRequirement(models.Model):

    _name = "hr.job.requirement"

    name = fields.Char()


# =====================================================
# REQUIREMENT LINE
# =====================================================

class HRjobRequirementLine(models.Model):

    _name = "hr.job.requirement.line"

    name = fields.Char()

    requirement_id = fields.Many2one(
        "hr.job.requirement"
    )

    job_id = fields.Many2one(
        "hr.job"
    )