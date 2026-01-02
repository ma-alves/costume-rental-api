import pytest
import pytest_asyncio
from factories import (
	CostumeFactory,
	CustomerFactory,
	UserFactory,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload  # , sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import (
	Costume,
	CostumeAvailability,
	Customer,
	Rental,
	User,
	table_registry,
)
from app.security import get_password_hash


@pytest_asyncio.fixture
async def test_session():
	engine = create_async_engine(
		'sqlite+aiosqlite:///:memory:',
		connect_args={'check_same_thread': False},
		poolclass=StaticPool,
	)
	# Legado de código para SQLite síncrono, NÃO APAGAR! Ref importante
	# TestSession = sessionmaker(bind=engine)
	# Base.metadata.create_all(engine)
	# yield TestSession()
	# Base.metadata.drop_all(engine)
	async with engine.begin() as conn:
		await conn.run_sync(table_registry.metadata.create_all)
	async with AsyncSession(engine, expire_on_commit=False) as session:
		yield session
	async with engine.begin() as conn:
		await conn.run_sync(table_registry.metadata.drop_all)


@pytest.fixture
def client(test_session: Session):
	def get_session_override():
		return test_session

	with TestClient(app) as client:
		app.dependency_overrides[get_session] = get_session_override
		yield client

	app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(test_session: Session):
	password = 'test1234'
	test_user = UserFactory(password=get_password_hash(password))

	test_session.add(test_user)
	await test_session.commit()
	await test_session.refresh(test_user)

	test_user.clean_password = 'test1234'

	return test_user


@pytest_asyncio.fixture
async def other_user(test_session: Session):
	password = 'test1234'
	test_user = UserFactory(password=get_password_hash(password), is_admin=False)

	test_session.add(test_user)
	await test_session.commit()
	await test_session.refresh(test_user)

	test_user.clean_password = 'test1234'

	return test_user


@pytest.fixture
def token(client: TestClient, user):
	response = client.post(
		'/auth/token',
		data={'username': user.email, 'password': user.clean_password},
	)
	return response.json()['access_token']


@pytest.fixture
def other_token(client: TestClient, other_user):
	response = client.post(
		'/auth/token',
		data={
			'username': other_user.email,
			'password': other_user.clean_password,
		},
	)
	return response.json()['access_token']


@pytest_asyncio.fixture
async def costume(test_session: Session):
	test_costume = CostumeFactory()

	test_session.add(test_costume)
	await test_session.commit()
	await test_session.refresh(test_costume)

	return test_costume


@pytest_asyncio.fixture
async def available_costume(test_session: Session):
	test_costume = CostumeFactory(availability=CostumeAvailability.AVAILABLE)

	test_session.add(test_costume)
	await test_session.commit()
	await test_session.refresh(test_costume)

	return test_costume


@pytest_asyncio.fixture
async def unavailable_costume(test_session: Session):
	test_costume = CostumeFactory(availability=CostumeAvailability.UNAVAILABLE)

	test_session.add(test_costume)
	await test_session.commit()
	await test_session.refresh(test_costume)

	return test_costume


@pytest_asyncio.fixture
async def customer(test_session: Session):
	test_customer = CustomerFactory()

	test_session.add(test_customer)
	await test_session.commit()
	await test_session.refresh(test_customer)

	return test_customer


@pytest_asyncio.fixture
async def rental(test_session: Session):
	costume = Costume(
		name='Test Costume',
		description='A costume for testing',
		fee=100.0,
		availability=CostumeAvailability.AVAILABLE,
	)
	test_session.add(costume)
	await test_session.commit()
	await test_session.refresh(costume)

	customer = Customer(
		cpf='12345678901',
		name='Test Customer',
		email='test@example.com',
		phone_number='12345678901',
		address='123 Test St',
	)
	test_session.add(customer)
	await test_session.commit()
	await test_session.refresh(customer)

	user = User(
		email='test@example.com',
		password=get_password_hash('test1234'),
		name='Test User',
		phone_number='12345678901',
		is_admin=True,
	)
	test_session.add(user)
	await test_session.commit()
	await test_session.refresh(user)

	test_rental = Rental(
		user_id=user.id,
		customer_id=customer.id,
		costume_id=costume.id,
	)

	test_session.add(test_rental)
	await test_session.commit()
	await test_session.refresh(test_rental)

	# eager loading
	# https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html#sqlalchemy.orm.joinedload
	rental_query = (
		select(Rental)
		.where(Rental.id == test_rental.id)
		.options(
			joinedload(Rental.costumes),
			joinedload(Rental.customers),
			joinedload(Rental.users),
		)
	)
	test_rental = await test_session.scalar(rental_query)

	return test_rental
