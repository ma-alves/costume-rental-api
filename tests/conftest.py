import pytest
import pytest_asyncio
from factories import (
	create_costume,
	create_user,
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
	Payment,
	PaymentStatus,
	Rental,
	Role,
	User,
	table_registry,
)
from app.security import get_password_hash


# teste local em SQLite assíncrono pois o processo
# é teimoso (refazer cenário e explicar)
@pytest_asyncio.fixture
async def test_session():
	engine = create_async_engine(
		'sqlite+aiosqlite:///:memory:',
		connect_args={'check_same_thread': False},
		poolclass=StaticPool,
	)
	# legado de código para SQLite síncrono, NÃO APAGAR! Ref importante
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
	test_user = await create_user(
		test_session,
		email='admin@example.com',
		password=password,
		role=Role.ADMIN,
	)
	test_user.clean_password = password
	return test_user


@pytest_asyncio.fixture
async def other_user(test_session: Session):
	password = 'test1234'
	test_user = await create_user(
		test_session,
		email='customer@example.com',
		password=password,
		role=Role.CUSTOMER,
	)
	test_user.clean_password = password
	return test_user


@pytest.fixture
def token(client: TestClient, user):
	response = client.post(
		'/api/v1/auth/token',
		data={'username': user.email, 'password': user.clean_password},
	)
	return response.json()['access_token']


@pytest.fixture
def other_token(client: TestClient, other_user):
	response = client.post(
		'/api/v1/auth/token',
		data={
			'username': other_user.email,
			'password': other_user.clean_password,
		},
	)
	return response.json()['access_token']


@pytest_asyncio.fixture
async def costume(test_session: Session):
	return await create_costume(test_session)


@pytest_asyncio.fixture
async def available_costume(test_session: Session):
	return await create_costume(
		test_session, availability=CostumeAvailability.AVAILABLE
	)


@pytest_asyncio.fixture
async def unavailable_costume(test_session: Session):
	return await create_costume(
		test_session, availability=CostumeAvailability.UNAVAILABLE
	)


@pytest_asyncio.fixture
async def customer(test_session: Session):
	return await create_user(
		test_session, email='customer@example.com', role=Role.CUSTOMER
	)


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

	customer = User(
		cpf='12345678901',
		name='Test Customer',
		email='customer@example.com',
		passwordHash=get_password_hash('test1234'),
		phone='12345678901',
		address='123 Test St',
		role=Role.CUSTOMER,
	)
	test_session.add(customer)
	await test_session.commit()
	await test_session.refresh(customer)

	admin_user = User(
		email='admin@example.com',
		passwordHash=get_password_hash('test1234'),
		name='Test Admin',
		phone='12345678901',
		role=Role.ADMIN,
		cpf='11122233344',
		address='456 Admin St',
	)
	test_session.add(admin_user)
	await test_session.commit()
	await test_session.refresh(admin_user)

	test_rental = Rental(
		user_id=admin_user.id,
		costume_id=costume.id,
	)

	test_session.add(test_rental)
	await test_session.commit()
	await test_session.refresh(test_rental)

	rental_query = (
		select(Rental)
		.where(Rental.id == test_rental.id)
		.options(
			joinedload(Rental.costumes),
			joinedload(Rental.users),
		)
	)
	test_rental = await test_session.scalar(rental_query)

	return test_rental


@pytest_asyncio.fixture
async def customer_rental(
	test_session: Session, other_user: User, available_costume: Costume
):
	rental = Rental(
		user_id=other_user.id,
		costume_id=available_costume.id,
	)
	test_session.add(rental)
	await test_session.commit()
	await test_session.refresh(rental)
	return rental


@pytest_asyncio.fixture
async def customer_payment(test_session: Session, customer_rental: Rental):
	payment = Payment(
		rental_id=customer_rental.id,
		stripe_payment_intent_id='pi_123456789',
		amount=10000,
		status=PaymentStatus.PENDING,
		currency='brl',
	)
	test_session.add(payment)
	await test_session.commit()
	await test_session.refresh(payment)
	return payment
