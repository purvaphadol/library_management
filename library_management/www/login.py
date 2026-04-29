# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

# WHY THIS FILE EXISTS:
# TemplatePage resolves the .py module from the SAME app directory as the .html.
# Since our www/login.html overrides Frappe's, we must also provide a login.py
# so that the template context (logo, app_name, provider_logins, etc.) is populated.
# This is a copy of frappe/www/login.py — all whitelisted methods remain at their
# original API paths (frappe.www.login.*) so nothing breaks.

from urllib.parse import urljoin, urlparse

import frappe
import frappe.utils
from frappe import _
from frappe.auth import LoginManager
from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_url
from frappe.utils.data import escape_html
from frappe.utils.html_utils import get_icon_html
from frappe.utils.jinja import guess_is_path
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys, redirect_post_login
from frappe.utils.password import get_decrypted_password
from frappe.website.utils import get_home_page

no_cache = True


def get_context(context):
	redirect_to = frappe.local.request.args.get("redirect-to")
	redirect_to = sanitize_redirect(redirect_to)

	if frappe.session.user != "Guest":
		if not redirect_to:
			if frappe.session.data.user_type == "Website User":
				redirect_to = get_home_page()
			else:
				redirect_to = "/app"

		if redirect_to != "login":
			frappe.local.flags.redirect_location = redirect_to
			raise frappe.Redirect

	context.no_header = True
	context.for_test = "login.html"
	context["title"] = "Login"
	context["body_class"] = "custom-login-page-body"
	context["provider_logins"] = []
	context["disable_signup"] = cint(frappe.get_website_settings("disable_signup"))
	context["disable_user_pass_login"] = cint(frappe.get_system_settings("disable_user_pass_login"))
	context["logo"] = get_app_logo()
	context["app_name"] = (
		frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name") or _("Frappe")
	)

	signup_form_template = frappe.get_hooks("signup_form_template")
	if signup_form_template and len(signup_form_template):
		path = signup_form_template[-1]
		if not guess_is_path(path):
			path = frappe.get_attr(signup_form_template[-1])()
	else:
		path = "frappe/templates/signup.html"

	if path:
		context["signup_form_template"] = frappe.get_template(path).render()

	providers = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "client_id", "base_url", "provider_name", "icon"],
		order_by="name",
	)

	for provider in providers:
		client_secret = get_decrypted_password(
			"Social Login Key", provider.name, "client_secret", raise_exception=False
		)
		if not client_secret:
			continue

		icon = None
		if provider.icon:
			if provider.provider_name == "Custom":
				icon = get_icon_html(provider.icon, small=True)
			else:
				icon = f"<img src={escape_html(provider.icon)!r} alt={escape_html(provider.provider_name)!r}>"

		if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
			context.provider_logins.append(
				{
					"name": provider.name,
					"provider_name": provider.provider_name,
					"auth_url": get_oauth2_authorize_url(provider.name, redirect_to),
					"icon": icon,
				}
			)
			context["social_login"] = True

	if cint(frappe.db.get_value("LDAP Settings", "LDAP Settings", "enabled")):
		from frappe.integrations.doctype.ldap_settings.ldap_settings import LDAPSettings

		context["ldap_settings"] = LDAPSettings.get_ldap_client_settings()

	login_label = [_("Email")]

	if frappe.utils.cint(frappe.get_system_settings("allow_login_using_mobile_number")):
		login_label.append(_("Mobile"))

	if frappe.utils.cint(frappe.get_system_settings("allow_login_using_user_name")):
		login_label.append(_("Username"))

	context["login_label"] = f" {_('or')} ".join(login_label)

	context["login_with_email_link"] = frappe.get_system_settings("login_with_email_link")

	return context


def sanitize_redirect(redirect):
	"""Only allow redirect on same domain.

	Allowed redirects:
	- Same host e.g. https://frappe.localhost/path
	- Just path e.g. /app gets converted to https://frappe.localhost/app
	"""
	if not redirect:
		return redirect

	parsed_redirect = urlparse(redirect)

	parsed_request_host = urlparse(frappe.local.request.url)
	output_parsed_url = parsed_redirect._replace(
		netloc=parsed_request_host.netloc, scheme=parsed_request_host.scheme
	)
	if parsed_redirect.netloc:
		if parsed_request_host.netloc != parsed_redirect.netloc:
			output_parsed_url = output_parsed_url._replace(path="/app")
		else:
			output_parsed_url = output_parsed_url._replace(path=parsed_redirect.path)

	return output_parsed_url.geturl()
