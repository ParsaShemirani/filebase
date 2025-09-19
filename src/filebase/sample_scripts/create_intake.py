from filebase.connection import Session
from filebase.models import StorageDevice
from filebase.settings import intake_storage_device_path


with Session() as session:
    with session.begin():
        intake_device = StorageDevice(
            name="wdman",
            size=23094,
            path=intake_storage_device_path
        )
        session.add(intake_device)