import pytest
import pytest_asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import CostumeAvailability, table_registry
from app.security import get_password_hash

from factories import (
	CostumeFactory,
	CustomerFactory,
	EmployeeFactory,
	RentalFactory,
)


@pytest_asyncio.fixture
async def test_session():
	engine = create_async_engine(
		'sqlite+aiosqlite:///:memory:',
		connect_args={'check_same_thread': False},
		poolclass=StaticPool,
	)
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


@pytest.fixture
def employee(test_session: Session):
	password = 'test1234'
	test_employee = EmployeeFactory(password=get_password_hash(password))

	test_session.add(test_employee)
	test_session.commit()
	test_session.refresh(test_employee)

	test_employee.clean_password = 'test1234'

	return test_employee


@pytest.fixture
def other_employee(test_session: Session):
	password = 'test1234'
	test_employee = EmployeeFactory(
		password=get_password_hash(password), is_admin=False
	)

	test_session.add(test_employee)
	test_session.commit()
	test_session.refresh(test_employee)

	test_employee.clean_password = 'test1234'

	return test_employee


@pytest.fixture
def token(client: TestClient, employee):
	response = client.post(
		'/auth/token',
		data={'username': employee.email, 'password': employee.clean_password},
	)
	return response.json()['access_token']


@pytest.fixture
def other_token(client: TestClient, other_employee):
	response = client.post(
		'/auth/token',
		data={
			'username': other_employee.email,
			'password': other_employee.clean_password,
		},
	)
	return response.json()['access_token']


@pytest.fixture
def costume(test_session: Session):
	test_costume = CostumeFactory()

	test_session.add(test_costume)
	test_session.commit()
	test_session.refresh(test_costume)

	return test_costume


@pytest.fixture
def available_costume(test_session: Session):
	test_costume = CostumeFactory(availability=CostumeAvailability.AVAILABLE)

	test_session.add(test_costume)
	test_session.commit()
	test_session.refresh(test_costume)

	return test_costume


@pytest.fixture
def unavailable_costume(test_session: Session):
	test_costume = CostumeFactory(availability=CostumeAvailability.UNAVAILABLE)

	test_session.add(test_costume)
	test_session.commit()
	test_session.refresh(test_costume)

	return test_costume


@pytest.fixture
def customer(test_session: Session):
	test_customer = CustomerFactory()

	test_session.add(test_customer)
	test_session.commit()
	test_session.refresh(test_customer)

	return test_customer


@pytest.fixture
def rental(test_session: Session):
	test_rental = RentalFactory()

	test_session.add(test_rental)
	test_session.commit()
	test_session.refresh(test_rental)

	return test_rental
