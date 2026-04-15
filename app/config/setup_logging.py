import logging


def setup_logging(level: str | int = logging.INFO):
	formatter = logging.Formatter(
		'{asctime} - {levelname} - {name} - {message}',
		style='{',
		datefmt='%Y-%m-%d %H:%M',
	)

	handler = logging.StreamHandler()
	handler.setFormatter(formatter)

	root_logger = logging.getLogger()
	root_logger.setLevel(level)
	root_logger.addHandler(handler)
