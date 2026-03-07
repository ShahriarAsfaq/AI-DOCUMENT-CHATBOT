from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'

    def create(self, validated_data):
        if not validated_data.get("title"):
            validated_data["title"] = validated_data["file"].name
        return super().create(validated_data)