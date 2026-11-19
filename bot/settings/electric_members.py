from db import mongodb


class ElectricMembers:
    available_members: list[int]

    async def update(self):
        deye_personals = await mongodb.get_all_deye_personals()
        members = []
        for deye in deye_personals:
            members.extend(deye.user_ids)

        self.available_members = members


electric_members = ElectricMembers()
