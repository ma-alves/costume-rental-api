from datetime import datetime, timedelta
from random import randint

import factory
import factory.fuzzy

from app.models import (
	Costume,
	CostumeAvailability,
	Customer,
	Rental,
	User,
)


class UserFactory(factory.Factory):
	class Meta:
		model = User

	# id = factory.Sequence(lambda n: n + 1)
	name = factory.Faker('name', locale='pt_BR')
	email = factory.Faker('free_email')
	password = factory.LazyAttribute(lambda obj: f'{obj.name}1234')
	phone_number = factory.Faker('phone_number')
	is_admin = True


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
		model = Customer

	# id = factory.Sequence(lambda n: n + 1)
	cpf = factory.Faker('random_number', digits=11, fix_len=True)
	name = factory.Faker('name', locale='pt_BR')
	email = factory.Faker('free_email')
	phone_number = factory.Faker('phone_number')
	address = factory.Faker('address', locale='pt_BR')


# __init__() got unexpected argument 'users' | 'customers' | 'costumes'
# then int(1) it is!
class RentalFactory(factory.Factory):
	class Meta:
		model = Rental

	# users = factory.SubFactory(UserFactory)
	# customers = factory.SubFactory(CustomerFactory)
	# costumes = factory.SubFactory(CostumeFactory)

	# # id = factory.Sequence(lambda n: n + 1)
	# user_id = factory.SelfAttribute('users.id')
	# customer_id = factory.SelfAttribute('customers.id')
	# costume_id = factory.SelfAttribute('costumes.id')

	user_id = 1
	customer_id = 1
	costume_id = 1
	rental_date = datetime.now()
	return_date = factory.LazyAttribute(lambda obj: obj.rental_date + timedelta(days=7))
