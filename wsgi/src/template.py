from settings import settings
from model import Photo

class Template:
	@staticmethod
	def render(template_name, params = {}):
		template = settings.TEMPLATE_ENV.get_template(template_name)
		all_args = dict(params.items() + Template._get_common_args().items())
		return template.render(all_args)

	@staticmethod
	def _get_common_args ():
		common_args = {
			"base_url": settings.BASE_URL,
			"img_url": settings.IMG_URL,
			"thumbnail_url": settings.THUMBNAIL_URL,
			"med_thumb_size": Photo.MEDIUM_THUMB_SIZE
		}
		return common_args
