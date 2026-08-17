from app.domain.entities.child import Child
from app.domain.ports.repositories import ChildrenRepositoryPort
from app.extensions import db
from app.infrastructure.database.models import ChildModel


class SQLAlchemyChildrenRepository(ChildrenRepositoryPort):
    def save(self, child: Child) -> Child:
        if child.id is None:
            model = ChildModel(
                parent_id=child.parent_id,
                full_name=child.full_name,
                class_name=child.class_name,
            )
            db.session.add(model)
        else:
            model = db.session.get(ChildModel, child.id)
            if model is None:
                raise ValueError("Child not found")
            model.parent_id = child.parent_id
            model.full_name = child.full_name
            model.class_name = child.class_name

        db.session.commit()
        return self._to_entity(model)

    def list_by_parent(self, parent_id: int) -> list[Child]:
        models = ChildModel.query.filter_by(parent_id=parent_id).all()
        return [self._to_entity(model) for model in models]

    def find_by_class(self, class_name: str) -> list[Child]:
        models = ChildModel.query.filter_by(class_name=class_name).all()
        return [self._to_entity(model) for model in models]

    def find_by_id(self, child_id: int) -> Child | None:
        model = db.session.get(ChildModel, child_id)
        return self._to_entity(model) if model else None

    def delete(self, child_id: int) -> Child | None:
        model = db.session.get(ChildModel, child_id)
        if model is None:
            return None
        child = self._to_entity(model)
        db.session.delete(model)
        db.session.commit()
        return child

    def _to_entity(self, model: ChildModel) -> Child:
        return Child(
            id=model.id,
            parent_id=model.parent_id,
            full_name=model.full_name,
            class_name=model.class_name,
            created_at=model.created_at,
        )