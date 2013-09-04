from settings import Settings as S

class Template:
	# some common arguments for templates
	@staticmethod
	def get_common_args():
		return {
			"base_url": S.BASE_URL,
			"img_url": "%s/img" % S.BASE_URL,
			"thumbnail_url": "%s/img/thumbs" % S.BASE_URL,
			"site_name": S.SITE_NAME
		}

	@staticmethod
	def render(template_name, params = {}):
		template = S.TEMPLATE_ENV.get_template(template_name)
		all_args = dict(params.items() + Template.get_common_args().items())
		return template.render(all_args)
