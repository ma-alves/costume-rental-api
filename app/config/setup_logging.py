import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ContextVar is a way to store values that are isolated per async task / thread.
# Think of it like a global variable, but each concurrent request gets its own
# independent copy — changes in one request don't bleed into another.
# via sonnet 4.6
request_id_ctx: ContextVar[str | None] = ContextVar('request_id', default=None)
user_id_ctx: ContextVar[int | None] = ContextVar('user_id', default=None)


def set_request_id(req_id: str | None = None) -> str:
	request_id = req_id or str(uuid.uuid4())
	request_id_ctx.set(request_id)
	return request_id


def set_user_id(user_id: int | None) -> None:
	user_id_ctx.set(user_id)


def get_request_id() -> str | None:
	return request_id_ctx.get()


def get_user_id() -> int | None:
	return user_id_ctx.get()


class CustomJsonFormatter(logging.Formatter):
	def __init__(self, fmt: str | None = None, datefmt: str | None = None):
		super().__init__(fmt, datefmt)
		self.required_fields = [
			'timestamp',
			'level',
			'name',
			'message',
			'request_id',
			'user_id',
			'costume_id',
			'rental_id',
			'method',
			'path',
			'status_code',
		]

	def format(self, record: logging.LogRecord) -> str:
		log_obj: dict[str, Any] = {
			'timestamp': datetime.now(timezone.utc).isoformat(),
			'level': record.levelname,
			'name': record.name,
			'message': record.getMessage(),
		}

		if record.exc_info:
			log_obj['exc_info'] = self.formatException(record.exc_info)

		if record.stack_info:
			log_obj['stack_info'] = self.formatStack(record.stack_info)

		if hasattr(record, 'user_id') and record.user_id is not None:
			log_obj['user_id'] = record.user_id
		elif get_user_id() is not None:
			log_obj['user_id'] = get_user_id()

		if hasattr(record, 'costume_id') and record.costume_id is not None:
			log_obj['costume_id'] = record.costume_id

		if hasattr(record, 'rental_id') and record.rental_id is not None:
			log_obj['rental_id'] = record.rental_id

		if get_request_id() is not None:
			log_obj['request_id'] = get_request_id()

		if hasattr(record, 'method') and record.method is not None:
			log_obj['method'] = record.method

		if hasattr(record, 'path') and record.path is not None:
			log_obj['path'] = record.path

		if hasattr(record, 'status_code') and record.status_code is not None:
			log_obj['status_code'] = record.status_code

		for key, value in record.__dict__.items():
			if key not in (
				'name',
				'msg',
				'args',
				'created',
				'filename',
				'funcName',
				'levelname',
				'levelno',
				'lineno',
				'module',
				'msecs',
				'message',
				'pathname',
				'process',
				'processName',
				'relCreated',
				'stack_info',
				'exc_info',
				'exc_text',
				'taskName',
				'costume_id',
				'rental_id',
				'user_id',
				'method',
				'path',
				'status_code',
			):
				if not key.startswith('_'):
					log_obj[key] = value

		return json.dumps(log_obj, default=str)


def setup_logging(level: int | str = logging.INFO) -> None:
	root_logger = logging.getLogger()
	root_logger.setLevel(level)

	for handler in root_logger.handlers[:]:
		root_logger.removeHandler(handler)

	stream_handler = logging.StreamHandler(sys.stdout)
	stream_handler.setLevel(level)
	stream_handler.setFormatter(CustomJsonFormatter())
	root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
	return logging.getLogger(name)
