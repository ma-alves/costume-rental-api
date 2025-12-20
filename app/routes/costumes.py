from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import CostumeAvailability, Costume, Employee
from app.schemas import CostumeInput, CostumeList, CostumeOutput, Message
from app.security import get_current_employee


router = APIRouter(prefix='/costumes', tags=['costumes'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
Session = Annotated[AsyncSession, Depends(get_session)]


async def query_costume_by_id(session: Session, costume_id):
	query_db_costume = await session.scalar(
		select(Costume).where(Costume.id == costume_id)
	)

	if not query_db_costume:
		raise HTTPException(
			HTTPStatus.NOT_FOUND, detail='Costume not registered.'
		)

	return query_db_costume


@router.get('/', response_model=CostumeList)
async def get_costumes(
	session: Session,
	availability: CostumeAvailability = Query(None),
	skip: int = Query(None),
	limit: int = Query(None),
):
	query = select(Costume)

	if availability:
		query = await query.filter(Costume.availability == availability)

	costumes_scalar = await session.scalars(query.offset(skip).limit(limit))
	costumes = costumes_scalar.all()

	return {'costumes': costumes}


@router.get('/{costume_id}', response_model=CostumeOutput)
async def get_costume(session: Session, costume_id: int):
	db_costume = await query_costume_by_id(session, costume_id)
	return db_costume


@router.post('/', response_model=CostumeOutput, status_code=HTTPStatus.CREATED)
async def create_costume(
	session: Session,
	current_employee: CurrentEmployee,
	costume: CostumeInput,
):
	db_costume = await session.scalar(
		select(Costume).where(Costume.name == costume.name)
	)

	if db_costume:
		raise HTTPException(
			HTTPStatus.CONFLICT, detail='Costume already registered.'
		)

	db_costume = Costume(
		name=costume.name,
		description=costume.description,
		fee=costume.fee,
		availability=costume.availability,
	)

	session.add(db_costume)
	await session.commit()
	await session.refresh(db_costume)

	return db_costume


@router.put('/{costume_id}', response_model=CostumeOutput)
async def update_costume(
	session: Session,
	current_employee: CurrentEmployee,
	costume: CostumeInput,
	costume_id: int,
):
	db_costume = await query_costume_by_id(session, costume_id)

	db_costume.name = costume.name
	db_costume.description = costume.description
	db_costume.fee = costume.fee
	db_costume.availability = costume.availability

	await session.commit()
	await session.refresh(db_costume)

	return db_costume


@router.delete('/{costume_id}', response_model=Message)
async def delete_costume(
	current_employee: CurrentEmployee,
	session: Session,
	costume_id: int,
):
	db_costume = await query_costume_by_id(session, costume_id)

	await session.delete(db_costume)
	await session.commit()

	return {'message': 'Costume deleted.'}
