from datetime import datetime, timedelta
from random import randint

import factory
import factory.fuzzy

from app.models import (
	Costume,
	CostumeAvailability,
	Rental,
	Role,
	User,
)


class UserFactory(factory.Factory):
	class Meta:
		model = User

	name = factory.Faker('name', locale='pt_BR')
	email = factory.Faker('free_email')
	passwordHash = factory.LazyAttribute(lambda obj: f'{obj.name}1234')
	phone = factory.Faker('phone_number')
	role = Role.ADMIN
	cpf = factory.Faker('random_number', digits=11, fix_len=True)
	address = factory.Faker('address', locale='pt_BR')


class CostumeFactory(factory.Factory):
	class Meta:
		model = Costume

	# id = factory.Sequence(lambda n: n + 1)
	name = factory.Faker('name', locale='pt_BR')
	description = factory.Faker('text')
	fee = float(randint(0, 1000))
	availability = factory.fuzzy.FuzzyChoice(CostumeAvailability)


class CustomerFactory(factory.Factory):
	class Meta:
		model = User

	cpf = factory.Faker('random_number', digits=11, fix_len=True)
	name = factory.Faker('name', locale='pt_BR')
	email = factory.Faker('free_email')
	phone = factory.Faker('phone_number')
	address = factory.Faker('address', locale='pt_BR')
	passwordHash = factory.LazyAttribute(lambda obj: f'{obj.name}1234')
	role = Role.CUSTOMER


# __init__() got unexpected argument 'users' | 'customers' | 'costumes'
# then int(1) it is!
class RentalFactory(factory.Factory):
	class Meta:
		model = Rental

	user_id = 1
	costume_id = 1
	rental_date = datetime.now()
	return_date = factory.LazyAttribute(lambda obj: obj.rental_date + timedelta(days=7))
