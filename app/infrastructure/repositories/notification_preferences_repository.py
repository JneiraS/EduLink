from app.domain.ports.repositories import NotificationPreferencesPort
from app.extensions import db
from app.infrastructure.database.models import (
    ChannelNotificationSettingModel,
    UserNotificationSettingModel,
)


class SQLAlchemyNotificationPreferencesRepository(NotificationPreferencesPort):
    def get_global_enabled(self, user_id: int) -> bool:
        row = db.session.get(UserNotificationSettingModel, user_id)
        return row.global_enabled if row else True

    def set_global_enabled(self, user_id: int, enabled: bool) -> None:
        row = db.session.get(UserNotificationSettingModel, user_id)
        if row is None:
            row = UserNotificationSettingModel(
                user_id=user_id, global_enabled=enabled
            )
            db.session.add(row)
        else:
            row.global_enabled = enabled
        db.session.commit()

    def is_channel_enabled(self, user_id: int, channel_id: int) -> bool:
        row = db.session.get(
            ChannelNotificationSettingModel, (user_id, channel_id)
        )
        return row.enabled if row else True

    def set_channel_enabled(self, user_id: int, channel_id: int, enabled: bool) -> None:
        row = db.session.get(
            ChannelNotificationSettingModel, (user_id, channel_id)
        )
        if row is None:
            row = ChannelNotificationSettingModel(
                user_id=user_id, channel_id=channel_id, enabled=enabled
            )
            db.session.add(row)
        else:
            row.enabled = enabled
        db.session.commit()

    def list_channel_states(self, user_id: int) -> dict[int, bool]:
        rows = ChannelNotificationSettingModel.query.filter_by(
            user_id=user_id
        ).all()
        return {row.channel_id: row.enabled for row in rows}

    def is_enabled(self, user_id: int, channel_id: int) -> bool:
        return self.get_global_enabled(user_id) and self.is_channel_enabled(
            user_id, channel_id
        )