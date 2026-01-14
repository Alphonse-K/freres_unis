from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.models.id import IDType
from src.schemas.id import IDTypeCreate, IDTypeUpdate

class IDTypeService:

    @staticmethod
    def create(db: Session, data: IDTypeCreate) -> IDType:
        id_type = IDType(**data.model_dump())
        db.add(id_type)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="IDType with this name already exists"
            )
        db.refresh(id_type)
        return id_type

    @staticmethod
    def update(db: Session, id_type_id: int, data: IDTypeUpdate) -> IDType:
        id_type = db.query(IDType).filter_by(id=id_type_id).first()
        if not id_type:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="IDType not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(id_type, field, value)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="IDType with this name already exists"
            )

        db.refresh(id_type)
        return id_type

    @staticmethod
    def get(db: Session, id_type_id: int) -> IDType:
        id_type = db.query(IDType).filter_by(id=id_type_id).first()
        if not id_type:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="IDType not found")
        return id_type

    @staticmethod
    def list(db: Session) -> list[IDType]:
        return db.query(IDType).order_by(IDType.name).all()
