from typing import TypedDict


class PyrusValueFieldT(TypedDict):
    __type: str
    FieldId: int
    Value: int


class PyrusTextFieldT(TypedDict):
    __type: str
    FieldId: int
    Text: int


class PyrusBitFieldT(TypedDict):
    __type: str
    FieldId: int
    Bit: bool


class PyrusStrValuesFieldT(TypedDict):
    __type: str
    FieldId: int
    Values: list[str]


class PyrusIntValuesFieldT(TypedDict):
    __type: str
    FieldId: int
    Values: list[int]


class PyrusItemsFieldT(TypedDict):
    __type: str
    FieldId: int
    Items: list[PyrusStrValuesFieldT | PyrusIntValuesFieldT]


class PyrusCheckerStatusT(TypedDict):
    FileCheckerType: int
    FileCheckerVersion: int
    FileVerdict: int
    PersonalDataInFileInfo: int | None
    Status: int


class PyrusGuardInfoT(TypedDict):
    CanDownload: bool
    CheckerStatuses: list[PyrusCheckerStatusT]


class PyrusFileFieldT(TypedDict):
    GuardInfo: PyrusGuardInfoT
    HasPreviewImg: bool
    HasPreviewPdf: bool
    Id: int
    IsPdf: bool
    IsReference: bool
    IsText: bool
    Name: str
    RootId: int
    Signatures: list[str]
    Size: int
    Url: str


class PyrusFieldFilesT(TypedDict):
    __type: str
    FieldId: int
    ExistingFiles: list[PyrusFileFieldT]


class PyrusAmountFieldT(TypedDict):
    __type: str
    FieldId: int
    Amount: float


class PyrusDateFieldT(TypedDict):
    __type: str
    FieldId: int
    Date: str


class PyrusCurrentStepT(TypedDict):
    Name: str
    Num: int


class PyrusEntryT(TypedDict):
    __type: str
    Fields: list[
        PyrusValueFieldT
        | PyrusTextFieldT
        | PyrusBitFieldT
        | PyrusItemsFieldT
        | PyrusFieldFilesT
        | PyrusStrValuesFieldT
        | PyrusIntValuesFieldT
        | PyrusAmountFieldT
        | PyrusDateFieldT
    ]
    TemplateId: int
    AssigneeId: int
    CloseDate: str
    CreateDate: str
    CurrentStep: PyrusCurrentStepT
    CurrentStepApprovers: list[str]
    DueDate: str
    IsOverdued: bool
    LastActionDate: str
    LastImportantNoteId: int
    LastNoteId: int
    LastReadNoteId: int
    ProjectIds: list[int]
    TaskId: int
    WorkflowStepsCount: int
    WorkflowStepsDone: int


class TextValueT(TypedDict):
    __type: str
    FieldId: int
    Text: str


class CatalogItemT(TypedDict):
    Id: int


class CatalogValueT(TypedDict):
    __type: str
    FieldId: int
    Items: list[CatalogItemT]


class MoneyValueT(TypedDict):
    __type: str
    FieldId: int
    Amount: float | int


class DateValueT(TypedDict):
    __type: str
    FieldId: int
    Date: str


ValueT = TextValueT | MoneyValueT | DateValueT | CatalogValueT


class PyrusFilterT(TypedDict):
    FieldId: int
    OperatorId: int
    Values: list[ValueT]


class PyrusPayloadInnerT(TypedDict):
    ProjectId: int
    TemplateId: int
    ActiveOnly: bool
    MaxItemCount: int
    Filters: list[PyrusFilterT]
    TimeZoneSpan: int
    SortMode: int
    WithRegisterSettings: bool
    PersonCacheSign: str
    ProjectCacheSign: str
    CompactFormCacheSign: str
    Locale: int
    ApiSign: str
    SkipCounters: bool
    AccountId: int
    PersonProjectStamp: str


class PyrusPayloadT(TypedDict):
    req: PyrusPayloadInnerT


class PersonT(TypedDict):
    AvatarColor: str
    Email: str
    FirstName: str
    Id: int
    LastName: str
    Location: str
    MessengerType: int
    ObjectVersion: int
    OrganizationId: int
    PersonFlags: int
    PersonFlagsBinary: list[int]
    Rights: int
    WorkPhone: str
    ManagerId: int


class ScopeCacheT(TypedDict):
    Persons: list[PersonT]


class DataT(TypedDict):
    ScopeCache: ScopeCacheT
    Forms: list[PyrusEntryT]
