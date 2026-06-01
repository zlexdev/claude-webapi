"""Domain UUID NewTypes for stronger typing of API identifiers."""

from typing import NewType

OrgUUID = NewType("OrgUUID", str)
ConvUUID = NewType("ConvUUID", str)
ProjectUUID = NewType("ProjectUUID", str)
ArtifactUUID = NewType("ArtifactUUID", str)
MessageUUID = NewType("MessageUUID", str)
AccountUUID = NewType("AccountUUID", str)
DocUUID = NewType("DocUUID", str)
FileUUID = NewType("FileUUID", str)
