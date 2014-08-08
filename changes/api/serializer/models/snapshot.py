from changes.api.serializer import Serializer, register
from changes.models import Snapshot


@register(Snapshot)
class SnapshotSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'project': {
                'id': instance.project_id.hex,
            },
            'build': {
                'id': instance.build_id.hex if instance.build_id else None,
            },
            'status': instance.status,
            'dateCreated': instance.date_created,
        }