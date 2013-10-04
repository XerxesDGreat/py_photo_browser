class ObjectRegistry(object):
	"""
	Registry for constructed objects so they can be all broken down before the
	process ends
	"""
	objects = []

	@staticmethod
	def register(obj):
		ObjectRegistry.objects.append(obj)
	
	@staticmethod
	def destroy_all():
		for o in ObjectRegistry.objects:
			try:
				o.destroy()
			except:
				pass
