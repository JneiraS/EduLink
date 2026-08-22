import pytest

from app.application.use_cases.message_template_use_cases import (
    CreateMessageTemplate,
    DeleteMessageTemplate,
    ListMessageTemplates,
    UpdateMessageTemplate,
)
from app.domain.entities.message_template import MessageTemplate
from app.domain.entities.user import User, UserRole
from app.domain.errors import AuthorizationError, ValidationError


class InMemoryTemplates:
    def __init__(self):
        self.items = []

    def save(self, template):
        template.id = len(self.items) + 1
        self.items.append(template)
        return template

    def list_by_owner(self, owner_id):
        return [t for t in self.items if t.owner_id == owner_id]

    def find_by_id(self, template_id):
        return next((t for t in self.items if t.id == template_id), None)

    def delete(self, template_id):
        for index, template in enumerate(self.items):
            if template.id == template_id:
                return self.items.pop(index)
        return None

    def update(self, template_id, label, content):
        for template in self.items:
            if template.id == template_id:
                template.label = label
                template.content = content
                return template
        return None


def _actor(uid=1, role=UserRole.TEACHER):
    return User(
        id=uid,
        full_name="A",
        email="a@t.local",
        role=role,
        password_hash="x",
        is_active=True,
    )


def test_create_message_template():
    repo = InMemoryTemplates()
    use_case = CreateMessageTemplate(templates=repo)
    template = use_case.execute(_actor(), "Reponse", "Bonjour, nous sommes disponibles.")
    assert template.label == "Reponse"
    assert template.owner_id == 1
    assert template.id == 1


def test_create_message_template_requires_label():
    use_case = CreateMessageTemplate(templates=InMemoryTemplates())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "  ", "Contenu")


def test_create_message_template_rejects_oversized_label():
    use_case = CreateMessageTemplate(templates=InMemoryTemplates())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "x" * 81, "Contenu")


def test_create_message_template_requires_content():
    use_case = CreateMessageTemplate(templates=InMemoryTemplates())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "Label", "  ")


def test_create_message_template_rejects_oversized_content():
    use_case = CreateMessageTemplate(templates=InMemoryTemplates())
    with pytest.raises(ValidationError):
        use_case.execute(_actor(), "Label", "x" * 5001)


def test_list_message_templates_returns_own():
    repo = InMemoryTemplates()
    repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    repo.save(MessageTemplate(id=None, owner_id=2, label="B", content="c"))
    use_case = ListMessageTemplates(templates=repo)
    templates = use_case.execute(_actor(uid=1))
    assert [t.label for t in templates] == ["A"]


def test_delete_message_template_owner_only():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = DeleteMessageTemplate(templates=repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), template.id)
    assert repo.find_by_id(template.id) is not None


def test_delete_message_template_removes():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = DeleteMessageTemplate(templates=repo)
    use_case.execute(_actor(uid=1), template.id)
    assert repo.find_by_id(template.id) is None


def test_update_message_template_edits():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = UpdateMessageTemplate(templates=repo)
    updated = use_case.execute(_actor(uid=1), template.id, "Nouveau", "Contenu mis a jour")
    assert updated.label == "Nouveau"
    assert updated.content == "Contenu mis a jour"


def test_update_message_template_owner_only():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = UpdateMessageTemplate(templates=repo)
    with pytest.raises(AuthorizationError):
        use_case.execute(_actor(uid=2), template.id, "X", "y")


def test_update_message_template_not_found():
    repo = InMemoryTemplates()
    use_case = UpdateMessageTemplate(templates=repo)
    with pytest.raises(ValidationError):
        use_case.execute(_actor(uid=1), 999, "X", "y")


def test_update_message_template_requires_label():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = UpdateMessageTemplate(templates=repo)
    with pytest.raises(ValidationError):
        use_case.execute(_actor(uid=1), template.id, "  ", "y")


def test_update_message_template_requires_content():
    repo = InMemoryTemplates()
    template = repo.save(MessageTemplate(id=None, owner_id=1, label="A", content="c"))
    use_case = UpdateMessageTemplate(templates=repo)
    with pytest.raises(ValidationError):
        use_case.execute(_actor(uid=1), template.id, "X", "  ")