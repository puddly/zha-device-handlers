"""Hue gradient scenes, captured from the Hue app."""

from typing import Final

from zhaquirks.philips.hue_light_update import HueLightUpdate

HUE_GRADIENT_SCENES: Final = {
    "blossom": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000039d553d2955ba5287a9f697e25fb802800")
    )[0],
    "crocus": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000050389322f97f2b597343764cc664282800")
    )[0],
    "precious": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000007fa8838bb9789a786d7577499a773f2800")
    )[0],
    "narcissa": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000b0498a5c0a888fea89eb0b7ee15c742800")
    )[0],
    "beginnings": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000b3474def153e2ad42e98232c7483292800")
    )[0],
    "first_light": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000b28b7900e959d3f648a614389723362800")
    )[0],
    "horizon": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000488b7d6cbb750c6642f1133cc4033c2800")
    )[0],
    "valley_dawn": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000c1aa7de03a7a8ce861c7c4410d94412800")
    )[0],
    "sunflare": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000d0aa7d787a7daf197590154d6c14472800")
    )[0],
    "emerald_flutter": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000006a933977e34bb0d35e916468f246792800")
    )[0],
    "memento": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000f87318a3e31962331ec3532cceea892800")
    )[0],
    "resplendent": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000278b6d257a58efe84204273a35f5252800")
    )[0],
    "scarlet_dream": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000b02c654e4c5b45ab51fb0950d6c84d2800")
    )[0],
    "lovebirds": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000053ab84ea1a7e35fb7c098c73994c772800")
    )[0],
    "smitten": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000fe7b70a74b6aa42b65811b60550a592800")
    )[0],
    "glitz_and_glam": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000cc193cb9b845bad9521d1c77bf6c712800")
    )[0],
    "promise": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000258b606eca6b28d6382db445df26812800")
    )[0],
    "ruby_romance": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000000edb63cbcb6bac0c670b2d58204e572800")
    )[0],
    "city_of_love": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000055830e5cf31b6aa339d2ec70908b802800")
    )[0],
    "honolulu": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000dbfd59866c6378ec6c45cc765c0a822800")
    )[0],
    "savanna_sunset": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000005ae65c38c6c6b4b7573ca820fc9832800")
    )[0],
    "golden_pond": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000007e4a88cc4a8605db8728ec7b666c792800")
    )[0],
    "ruby_glow": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000095bb53ac2a56eb99591e095c54985e2800")
    )[0],
    "tropical_twilight": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000408523a0b636e777524c0a71a76c6e2800")
    )[0],
    "miami": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000022ec61e6d94902d83766c3305a43182800")
    )[0],
    "cancun": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000a7eb54673d55944e6265fd6e26bb842800")
    )[0],
    "rio": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000a26526088c51a74b58ea6b7137ba892800")
    )[0],
    "chinatown": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000b33e5b408e59d90d5b4c6c6360ac792800")
    )[0],
    "ibiza": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000014d6d708c73827b7b6c7a8887f98a2800")
    )[0],
    "osaka": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000d649510b5c4deb7c5d8b6d6d2b9b802800")
    )[0],
    "tokyo": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000d1c311665331d3451fd59c4e394c7b2800")
    )[0],
    "motown": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000055730e5db3156623306c533d7a235c2800")
    )[0],
    "fairfax": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000072d34a3664477d7a61581d5fc08e5b2800")
    )[0],
    "galaxy": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000a6cb638b2a4f8cfa549bb9549ff73a2800")
    )[0],
    "starlight": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000008d897134a9653ec854d2963ed1d4282800")
    )[0],
    "blood_moon": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000202a6987c8599ee647ec632779c3142800")
    )[0],
    "arctic_aurora": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000082548922057511046571c32d5b93192800")
    )[0],
    "moonlight": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000055730e5e9320c1832e96243ebec7652800")
    )[0],
    "nebula": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000026c852e106460d653ee745342964142800")
    )[0],
    "sundown": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000f37c68157c6d8efa755ac5512e24332800")
    )[0],
    "blue_lagoon": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000088c3623975699ea672a0c8831ada6d2800")
    )[0],
    "palm_beach": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000005ec4679ba56077f85a80ea64639c6a2800")
    )[0],
    "lake_placid": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000002eab69239a692d996552c54c39743a2800")
    )[0],
    "mountain_breeze": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000df843d2355419195465a98674ca97b2800")
    )[0],
    "lake_mist": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000e3286f39b96859f86266e54ded943f2800")
    )[0],
    "ocean_dawn": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000005cf9779da97105b96b07485e32564a2800")
    )[0],
    "frosty_dawn": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000006d6883bca87e3029758ec9722d6a722800")
    )[0],
    "sunday_morning": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000002c586dc6f87345997c63f983f777892800")
    )[0],
    "emerald_isle": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000e535628dc57ed2667d8b687d1e2a812800")
    )[0],
    "spring_blossom": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000a8b75fd0c75826b851a7094d305b652800")
    )[0],
    "midsummer_sun": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000002984799984dd29848eba836c0b7f2800")
    )[0],
    "autumn_gold": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000435a7817aa7ba3f979a8a981f3c9852800")
    )[0],
    "spring_lake": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000004a976d3347736e677561b77a4b07812800")
    )[0],
    "winter_mountain": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000002c555c68c55d7c555ef165606136622800")
    )[0],
    "midwinter": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000bda5532c554dbd254cd5a4428d94392800")
    )[0],
    "amber_bloom": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000739d67f2bc7372ec78a0ab78be8a6f2800")
    )[0],
    "lily": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000009cfc76c5ab793d4a6a1a9b586b9c522800")
    )[0],
    "painted_sky": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000d1c424c3d63783384c3f7a6a83bd6d2800")
    )[0],
    "winter_beauty": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000e2335ea7b4942467952db986a7ab7b2800")
    )[0],
    "orange_fields": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000409c69694c79eafa88498a8fb867aa2800")
    )[0],
    "forest_adventure": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000023999bbd76b363d4b674d3415fb3222800")
    )[0],
    "blue_planet": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000037a7a3a403b489737b2b746e6873362800")
    )[0],
    "soho": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000c52c4e220b6eed8a53d404192b04782800")
    )[0],
    "vapor_wave": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000e1c32401251acb183ac31b8051ea842800")
    )[0],
    "magneto": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000077b3286d9340b9e3662d99943c9b852800")
    )[0],
    "tyrell": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000ef4419a898370ea84698353574434e2800")
    )[0],
    "disturbia": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000084f371a4845e6998388c3b4f57ce582800")
    )[0],
    "hal": HueLightUpdate.deserialize(
        bytes.fromhex("50010400135000000075f351a6244cf6dc5d480c658cda862800")
    )[0],
    "golden_star": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000007a4a8702eb8372ac7892cd61d51e5c2800")
    )[0],
    "under_the_tree": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000001de498b9a3cc0c9b8563bb6cc1ae5d2800")
    )[0],
    "silent_night": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000009e296a245a6f660a75086b70953b6e2800")
    )[0],
    "rosy_sparkle": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000810967c63a6cb2aa5ea7094eddd73c2800")
    )[0],
    "festive_fun": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000005a9318de53123e9414fdcc67839d612800")
    )[0],
    "colour_burst": HueLightUpdate.deserialize(
        bytes.fromhex("500104001350000000f2731ff0c6266a6c64246e57d4f98f2800")
    )[0],
    "crystalline": HueLightUpdate.deserialize(
        bytes.fromhex("5001040013500000006ea96a92a85e58074e18543d9cf3332800")
    )[0],
}
