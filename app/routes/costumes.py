from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import CostumeAvailability, Costume, Employee
from app.schemas import CostumeInput, CostumeList, CostumeOutput, Message
from app.security import get_current_employee


router = APIRouter(prefix='/costumes', tags=['costumes'])

CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
SessionDep = Annotated[Session, Depends(get_session)]


def query_costume_by_id(session: SessionDep, costume_id):
	query_db_costume = session.scalar(
		select(Costume).where(Costume.id == costume_id)
	)

	if not query_db_costume:
		raise HTTPException(
			HTTPStatus.NOT_FOUND, detail='Costume not registered.'
		)

	return query_db_costume


@router.get('/', response_model=CostumeList)
def get_costumes(
	session: SessionDep,
	availability: CostumeAvailability = Query(None),
	skip: int = Query(None),
	limit: int = Query(None),
):
	query = select(Costume)

	if availability:
		query = query.filter(Costume.availability == availability)

	costumes = session.scalars(query.offset(skip).limit(limit)).all()

	return {'costumes': costumes}


@router.get('/{costume_id}', response_model=CostumeOutput)
def get_costume(session: SessionDep, costume_id: int):
	return query_costume_by_id(session, costume_id)


@router.post('/', response_model=CostumeOutput, status_code=HTTPStatus.CREATED)
def create_costume(
	session: SessionDep,
	current_employee: CurrentEmployee,
	costume: CostumeInput,
):
	db_costume = session.scalar(
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
	session.commit()
	session.refresh(db_costume)

	return db_costume


@router.put('/{costume_id}', response_model=CostumeOutput)
def update_costume(
	session: SessionDep,
	current_employee: CurrentEmployee,
	costume: CostumeInput,
	costume_id: int,
):
	db_costume = query_costume_by_id(session, costume_id)

	db_costume.name = costume.name
	db_costume.description = costume.description
	db_costume.fee = costume.fee
	db_costume.availability = costume.availability
	session.commit()
	session.refresh(db_costume)

	return db_costume


@router.delete('/{costume_id}', response_model=Message)
def delete_costume(
	current_employee: CurrentEmployee,
	session: SessionDep,
	costume_id: int,
):
	db_costume = query_costume_by_id(session, costume_id)

	session.delete(db_costume)
	session.commit()

	return {'message': 'Costume deleted.'}
