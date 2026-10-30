'use strict';
// Compiled, reviewed program identities; never loaded from data or settings.
// This literal declaration is the sole recursive native table exclusion.
function freeze(value){if(value&&typeof value==='object'){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
const APPLICATION_SPECS=freeze({
  "melange": {
    "schemaVersion": 1,
    "appId": "melange",
    "contractId": "melange.public-data.v1",
    "programFiles": [
      {
        "root": "bootstrap",
        "path": "data_release_fetch.py",
        "bytes": 29092,
        "sha256": "6b55d468ecd71a04fb19838ac9cab9007488e96f2af92ef0881aa121030e29b7"
      },
      {
        "root": "bootstrap",
        "path": "desktop_audit.py",
        "bytes": 2393,
        "sha256": "2e790d8e19258bfe22b0506daad9e772277bbae3ef0634d99090e15acbb5e9a7"
      },
      {
        "root": "bootstrap",
        "path": "desktop_backend.py",
        "bytes": 41490,
        "sha256": "ad0b69f7faecd08eebc0011b7ec4857a26398874d87a4cbe3dce0a183f2db025"
      },
      {
        "root": "bootstrap",
        "path": "desktop_credentials.py",
        "bytes": 7888,
        "sha256": "ca892d3430a915596cde1d23ba1882426e257d9d9d40a4e00c04fba8a907d860"
      },
      {
        "root": "bootstrap",
        "path": "desktop_figure_renderer.py",
        "bytes": 2940,
        "sha256": "394168ece62af6f4039ffd2c8bf43b1365d99315710e758b05509f6a34b8adac"
      },
      {
        "root": "bootstrap",
        "path": "desktop_migrations.py",
        "bytes": 6536,
        "sha256": "46a58eeeb30e38fed26951e9c77ec997b80896e8773640fb9db95025d20e55b7"
      },
      {
        "root": "bootstrap",
        "path": "melange_bootstrap.py",
        "bytes": 2575,
        "sha256": "df23dce77aa9f975dfd018fb0c197c122308c0565944acefa93851e9f59e36cc"
      },
      {
        "root": "bootstrap",
        "path": "melange_data_paths.py",
        "bytes": 2011,
        "sha256": "83d8ef21161d1b9ae2ac816e7f26f7dfd1decc721c5ff05831ceb5574aaf2717"
      },
      {
        "root": "bootstrap",
        "path": "melange_module_data.py",
        "bytes": 9016,
        "sha256": "194ebad5d2ba0b4352019ca4077a20630b583fa9eb49578d035ced441a0c788a"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_payroll_normalize.py",
        "bytes": 32957,
        "sha256": "04d6db1ee363749550113aaf597319e097c3b6adf0213c38af3914eeae982301"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_payroll_projection.py",
        "bytes": 10725,
        "sha256": "3e0867801eb6ad607db6feb9928d78d3a41f7f1cc6e99b213e7b5d84f7c0795f"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_provenance.py",
        "bytes": 22634,
        "sha256": "d99456e6e133d365eef28cc0a9ec2de0a10d3fcf3615a00a576fa57ebea16278"
      },
      {
        "root": "bootstrap",
        "path": "mentat_layout.py",
        "bytes": 8400,
        "sha256": "9d567b8c07d8e0f03750a1491bc789e53bc0a480e4ab6913cb74bf7a53efadec"
      },
      {
        "root": "bootstrap",
        "path": "mentat_module_data.py",
        "bytes": 15031,
        "sha256": "87faca3b7be91404af809794f9534b01cf21d5e3b415466425fb31f9d905414a"
      },
      {
        "root": "bootstrap",
        "path": "module_application_contracts.py",
        "bytes": 19080,
        "sha256": "97b5b09f156adaa325768540b6c2bf72fbec5e8830e069f3f58f8095c7400095"
      },
      {
        "root": "bootstrap",
        "path": "module_catalogue_cache.py",
        "bytes": 6447,
        "sha256": "e469430b58aab667a354dc69b1e4b4414492b2d0b5b4ed625eee1a7ecdf77373"
      },
      {
        "root": "bootstrap",
        "path": "module_data_handoff.py",
        "bytes": 17615,
        "sha256": "f13ece0efa0ec4c1a7ab5e663f81a7a60b690ef346cd36819fe4a163b977c85e"
      },
      {
        "root": "bootstrap",
        "path": "module_data_launch.py",
        "bytes": 19712,
        "sha256": "2d7ea9886bc6ed2d3ff0274b16ea204fed974b3a24c096bf1c3d75c2283c869d"
      },
      {
        "root": "bootstrap",
        "path": "module_data_snapshot.py",
        "bytes": 12529,
        "sha256": "4f86f84e0d660ca7cdfaa9a941280d30c504cea1dc5624d509f6d1bee4cecf80"
      },
      {
        "root": "bootstrap",
        "path": "module_public_input_installers.py",
        "bytes": 18820,
        "sha256": "ec9992465a4410199c92428b5a97ffefdeb6d55c0ab9e1152f3a9a956fa6f9ba"
      },
      {
        "root": "bootstrap",
        "path": "native_access_state.py",
        "bytes": 7998,
        "sha256": "f956200a5094bf7c4ad93f75b5b41527a7c9356440069be92eac84b05a6c9277"
      },
      {
        "root": "bootstrap",
        "path": "native_credentials.py",
        "bytes": 13908,
        "sha256": "93f3c940adc135e61012ad7ecfe67bb57eac488c3b68be57e0d98e6df9babb65"
      },
      {
        "root": "bootstrap",
        "path": "terrier_district.py",
        "bytes": 7906,
        "sha256": "c7d3a9215b437a0b8d209d6bedba72fd32016fde052c91b889e1196ba40a3641"
      },
      {
        "root": "bootstrap",
        "path": "terrier_github_snapshot.py",
        "bytes": 8384,
        "sha256": "bcc8c6753a370cca339b47692a1688e53c148909397e69f0f70f9b9e820a4e79"
      },
      {
        "root": "bootstrap",
        "path": "terrier_owner.py",
        "bytes": 4806,
        "sha256": "86a8d731975c0cbbbd00d6f61cae3c980c318d2345b06b64823e85b9ad88caa5"
      },
      {
        "root": "bootstrap",
        "path": "terrier_standalone.py",
        "bytes": 15342,
        "sha256": "077f5936fca26cab3e382d34d6993f452d2b657ba951656362552bbcc4afa8e7"
      },
      {
        "root": "source",
        "path": "fec/lane_file_io.py",
        "bytes": 9077,
        "sha256": "b9b3adefc6407d0c21321e25b46ce8cf5b74d7ebbda69fca26ba8d8fb073f2f7"
      },
      {
        "root": "source",
        "path": "fec/paths.py",
        "bytes": 10280,
        "sha256": "88cebc6f534f5c30351bdc3daadbf58f666a604b58f8dea187aff66c39f64aa6"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/__init__.py",
        "bytes": 342,
        "sha256": "c999434f0ba900fc74c2452b19a545327eec459e8f0b8ad5b32ca7bc1c93370d"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/closeness_math.py",
        "bytes": 16972,
        "sha256": "9bad28845a057871ff829c673c2ac59f83674c85009eb286d2b097dda04d3dc5"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/lda_employment.py",
        "bytes": 38703,
        "sha256": "77e57e94cb73afb715e01ac0d015836dd0ce1ca1325fbe40d7dc2247590d74fb"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/lda_status_labels.py",
        "bytes": 19839,
        "sha256": "3c4b288e6bcdcaf86bd197d24efaaec3cb71831cff174a7f5cb22228ba9b3f77"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/littlesis_contract.py",
        "bytes": 9877,
        "sha256": "c772e4be0d2fbc1358d44df0330aa8bf06bfd3664703d75accdad0732615bf86"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/member_context.py",
        "bytes": 5310,
        "sha256": "84940f2cf1a438fd3ae1585e23f94d78abd43d55dde21f6eb8460b840919ae6d"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/name_standard.py",
        "bytes": 61722,
        "sha256": "5d4f9d06245bca93f01a5ca4abd5b5b428cc3bb1bdd4ea178d771e76e8e9e9fc"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/publication.py",
        "bytes": 74571,
        "sha256": "ddc437115b0da21663798f7aabfa5f93c2ac8364dd8b3b8cd9951a96a9e69958"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/ranking_math.py",
        "bytes": 4042,
        "sha256": "9588869cab752a5e2f005c611c8a4bb72538863b3b56a098c8b7976591e044d6"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/relationship_uncertainty.py",
        "bytes": 2993,
        "sha256": "625bd510aa7bd5e5432f74611a20e3a207720beaf4401d381de554f76d3758f3"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/schema_validation.py",
        "bytes": 10345,
        "sha256": "3fac36fa12350f27a522dd02a8a2efcd699b9b3e51772b829de47137d7e5f072"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/source_manifest.py",
        "bytes": 13351,
        "sha256": "9dc74fdfe846a5c5abadc91f776820d9a102d0ef1becd98419297e133e36ec90"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/source_native_corpus.py",
        "bytes": 29908,
        "sha256": "f78d98b57b6c8db3869980dec54f5c1654910348f98b49ff24b6209672d239b9"
      },
      {
        "root": "source",
        "path": "fec/staffer_network/validate.py",
        "bytes": 2940,
        "sha256": "15d2815e2bd78c60b21907438eea8287749b374976cb927b69b35fe701c48c3f"
      },
      {
        "root": "source",
        "path": "fec/surfaces/demand_data.py",
        "bytes": 13692,
        "sha256": "433d2dc3802e02efc925ac433009dff951d93fb6047ce81961ba5a4cf01ec885"
      },
      {
        "root": "source",
        "path": "fec/surfaces/melange_dashboard.py",
        "bytes": 5050,
        "sha256": "23f93d488261ccdd905d3914afb3a6da2198e273709be6353012b16e17abfcbf"
      },
      {
        "root": "source",
        "path": "fec/surfaces/melange_public_data.py",
        "bytes": 24883,
        "sha256": "8961c04eb7e29c20544645b9b56089bbb889594d7bd6acab364c6589ee05c36a"
      },
      {
        "root": "source",
        "path": "fec/surfaces/melange_public_pages.py",
        "bytes": 9091,
        "sha256": "3c7b90171fbcfd35eb6ebeeea0e5aa7037c92c864f09026f029cccf9390a6a07"
      },
      {
        "root": "source",
        "path": "fec/surfaces/public_data/index.html",
        "bytes": 1450,
        "sha256": "ac66f6a911a487d96c5bdfc83bd9196b140a01f19a402ff0d8d592ec4dafbe37"
      },
      {
        "root": "source",
        "path": "fec/surfaces/public_data/public-data.css",
        "bytes": 1611,
        "sha256": "35232e61a09f9267295e0e589e731fa7836fdda0c41fdb64711b4b34e008f6ad"
      },
      {
        "root": "source",
        "path": "fec/surfaces/public_data/public-data.js",
        "bytes": 6223,
        "sha256": "f932fe54e2287c3759bd5ffb7a4ec0eaf5824631fee8f6f9b186aa539addc510"
      },
      {
        "root": "source",
        "path": "fec/surfaces/source_capture.py",
        "bytes": 4961,
        "sha256": "e7f4d8e3cb572aa62c8b1088667aff855c4d355e3fa25cb2d4a3d703852d9b57"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_activity_index.py",
        "bytes": 17867,
        "sha256": "ff37d78da0f7f26f5493c9493ae8765e3dbe0801432b49dfea8e386dff2802a4"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_assertions.py",
        "bytes": 4127,
        "sha256": "2472ab8483e398b2db756fd854605eaeeab5eda6a60dff25c57e74f355b4c490"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_closeness_routes.py",
        "bytes": 59888,
        "sha256": "71ce4f0d5c212f31d75aa70aee2c1cf36468465938d487ab4549f5e5861570bf"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_connection_facts.py",
        "bytes": 20380,
        "sha256": "d0b6ed85ada0ecb8eb0527f0137ca35a1ab1971f2d9be49bb1ad5714e0be5aff"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_contacts.py",
        "bytes": 7929,
        "sha256": "0dc0bbbc03548fcb0fb2a46ca6ffd7ba271ad95710136696cafd81fe3268026a"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_distinct_routes.py",
        "bytes": 8244,
        "sha256": "9d5668fc84dfc51136f8b56aca72fcc3d8dbeac691dcb5acb841b5f829c5dd12"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_ecosystem_routes.py",
        "bytes": 8561,
        "sha256": "154037eab44fc1111e9b66ffe533eb41f72b93fd00a6dbd0d2a328fe050041f6"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_graph_snapshot.py",
        "bytes": 33756,
        "sha256": "c5b3e3eff218d12e655d87e26ed64c035bf8c078e163edc45e552cdbedb7e111"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_groups_index.py",
        "bytes": 17783,
        "sha256": "aa1a1d177a002af52c27d9f15c0ff6461b198620f730f8d2b4ce41966ed0c0af"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_identity_auto.py",
        "bytes": 20815,
        "sha256": "62fb5594c84ec5fd8356cfd81cbbb1f37fdf85431af2a3751e657335d82bb1b9"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_identity_records.py",
        "bytes": 6396,
        "sha256": "de6436e19dca045e4ad428865e2fd5a5622f90d9240ceecc8ab11aff6ffd0a6a"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_identity_resolution.py",
        "bytes": 13848,
        "sha256": "24e1a7151eaa7545092957012d489610bc2493778491e60d92e10a1f2d7163a9"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_identity_web.py",
        "bytes": 35012,
        "sha256": "52672815406b93ca6d4eb571f3a59c45816ba2784e26644587a2e5ab0248c6c4"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_lda_catalog.py",
        "bytes": 9418,
        "sha256": "7b2f723f51caffac1bdb53f2aeeb7a9adde4ea476a616359e88001554a439e87"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_live_generation.py",
        "bytes": 19960,
        "sha256": "acad5aeb739407d1f25972da4416cacc3bd995a692735bba9c860fd085c262d3"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_live_server.py",
        "bytes": 55891,
        "sha256": "9d6b348912be25330798c621dfc2e769c5cf52680b5fc1e1dba20d127dbd434c"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_live_service.py",
        "bytes": 142671,
        "sha256": "f69e233c2d2304da160a0bad3267c4272cf74bd5c8d7c5d6686fe581cd76dbcc"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_network_explorer.py",
        "bytes": 19362,
        "sha256": "0e75d11d4978e383027ab878d067828c200d148bbaa5b6101d454d9101b5d142"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_network_scope.py",
        "bytes": 1271,
        "sha256": "ebff4c98e8fdf4d3ba6285fab18baa815d8fde2aadbe4e66189206f74d8b24fb"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_office_routes.py",
        "bytes": 3858,
        "sha256": "cbc44bf31b8c372a8decc656cb782caaafec16f9af275e89fc5aa8b713d957fe"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_overlap_routes.py",
        "bytes": 19624,
        "sha256": "312bca42eede3304731af35075c6e8920717fb9c4b000d2dd01de3dd19a7cb54"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_payroll_identity.py",
        "bytes": 3807,
        "sha256": "3fe4330654b54e5595acce346138a47b90534ee8f2bda529b4e66b80f2813cd2"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_people_graph.py",
        "bytes": 8733,
        "sha256": "4aa6e32165d0cad7c7b0106921041c1a0ea5051142bec37911605eb379911635"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_person_inventory.py",
        "bytes": 20152,
        "sha256": "a983c11dd430007a0fa047a966904902ea9f0c62a9551a20ee3825ca16eda605"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_reconciled_evidence.py",
        "bytes": 9619,
        "sha256": "58c637ed81eb92475fd0922b7c377a34c18850282f2bf86eada8faea122617b8"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_route_cancel.py",
        "bytes": 859,
        "sha256": "3e8b003f4bea16582927cb21de3d3276175763d55d45efed02a73ab754e4e9df"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_routing.py",
        "bytes": 45248,
        "sha256": "436d495293c274a925b1a66169b558f18fac58301db4adab4d98db200f79446a"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_routing_evidence.py",
        "bytes": 13656,
        "sha256": "339ae210ed0098aee8a3d0dd9b71fa790b1bd83ea9739746eab706c4f0414dc0"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_search_index.py",
        "bytes": 11262,
        "sha256": "0e03bf444a671909b87adbf7745c1dd0838eda56f726f05a6077872d2c16e497"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_source_catalog.py",
        "bytes": 15048,
        "sha256": "e48711154b766edcb15fd1ab2812cd0653fbb1b2e4901225da6500405eecda7d"
      },
      {
        "root": "source",
        "path": "fec/surfaces/staffer_work_sources.py",
        "bytes": 5120,
        "sha256": "c2b7735d3a949d8599a0355500c04efface0903144bc8ad7523fdee81ac2dee0"
      }
    ],
    "programFingerprint": "e0668fea664c3e350bc7ba46de10bc48af30acabac66757bdbba8d6b1c4b46e6",
    "requiredKinds": [
      "melange.official-payroll-observations.v1"
    ],
    "publicReaders": [
      "melange.public-data.catalogue",
      "melange.public-data.provenance",
      "melange.public-data.observations"
    ],
    "privateBoundaries": [
      "melange.original.dashboard",
      "melange.original.source-root"
    ],
    "startupTimeoutMs": 600000
  },
  "mentat": {
    "schemaVersion": 1,
    "appId": "mentat",
    "contractId": "mentat.public-data.v1",
    "programFiles": [
      {
        "root": "bootstrap",
        "path": "data_release_fetch.py",
        "bytes": 29092,
        "sha256": "6b55d468ecd71a04fb19838ac9cab9007488e96f2af92ef0881aa121030e29b7"
      },
      {
        "root": "bootstrap",
        "path": "desktop_audit.py",
        "bytes": 2393,
        "sha256": "2e790d8e19258bfe22b0506daad9e772277bbae3ef0634d99090e15acbb5e9a7"
      },
      {
        "root": "bootstrap",
        "path": "desktop_backend.py",
        "bytes": 41490,
        "sha256": "ad0b69f7faecd08eebc0011b7ec4857a26398874d87a4cbe3dce0a183f2db025"
      },
      {
        "root": "bootstrap",
        "path": "desktop_credentials.py",
        "bytes": 7888,
        "sha256": "ca892d3430a915596cde1d23ba1882426e257d9d9d40a4e00c04fba8a907d860"
      },
      {
        "root": "bootstrap",
        "path": "desktop_figure_renderer.py",
        "bytes": 2940,
        "sha256": "394168ece62af6f4039ffd2c8bf43b1365d99315710e758b05509f6a34b8adac"
      },
      {
        "root": "bootstrap",
        "path": "desktop_migrations.py",
        "bytes": 6536,
        "sha256": "46a58eeeb30e38fed26951e9c77ec997b80896e8773640fb9db95025d20e55b7"
      },
      {
        "root": "bootstrap",
        "path": "melange_bootstrap.py",
        "bytes": 2575,
        "sha256": "df23dce77aa9f975dfd018fb0c197c122308c0565944acefa93851e9f59e36cc"
      },
      {
        "root": "bootstrap",
        "path": "melange_data_paths.py",
        "bytes": 2011,
        "sha256": "83d8ef21161d1b9ae2ac816e7f26f7dfd1decc721c5ff05831ceb5574aaf2717"
      },
      {
        "root": "bootstrap",
        "path": "melange_module_data.py",
        "bytes": 9016,
        "sha256": "194ebad5d2ba0b4352019ca4077a20630b583fa9eb49578d035ced441a0c788a"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_payroll_normalize.py",
        "bytes": 32957,
        "sha256": "04d6db1ee363749550113aaf597319e097c3b6adf0213c38af3914eeae982301"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_payroll_projection.py",
        "bytes": 10725,
        "sha256": "3e0867801eb6ad607db6feb9928d78d3a41f7f1cc6e99b213e7b5d84f7c0795f"
      },
      {
        "root": "bootstrap",
        "path": "melange_public_provenance.py",
        "bytes": 22634,
        "sha256": "d99456e6e133d365eef28cc0a9ec2de0a10d3fcf3615a00a576fa57ebea16278"
      },
      {
        "root": "bootstrap",
        "path": "mentat_layout.py",
        "bytes": 8400,
        "sha256": "9d567b8c07d8e0f03750a1491bc789e53bc0a480e4ab6913cb74bf7a53efadec"
      },
      {
        "root": "bootstrap",
        "path": "mentat_module_data.py",
        "bytes": 15031,
        "sha256": "87faca3b7be91404af809794f9534b01cf21d5e3b415466425fb31f9d905414a"
      },
      {
        "root": "bootstrap",
        "path": "module_application_contracts.py",
        "bytes": 19080,
        "sha256": "97b5b09f156adaa325768540b6c2bf72fbec5e8830e069f3f58f8095c7400095"
      },
      {
        "root": "bootstrap",
        "path": "module_data_handoff.py",
        "bytes": 17615,
        "sha256": "f13ece0efa0ec4c1a7ab5e663f81a7a60b690ef346cd36819fe4a163b977c85e"
      },
      {
        "root": "bootstrap",
        "path": "module_data_launch.py",
        "bytes": 19712,
        "sha256": "2d7ea9886bc6ed2d3ff0274b16ea204fed974b3a24c096bf1c3d75c2283c869d"
      },
      {
        "root": "bootstrap",
        "path": "module_data_snapshot.py",
        "bytes": 12529,
        "sha256": "4f86f84e0d660ca7cdfaa9a941280d30c504cea1dc5624d509f6d1bee4cecf80"
      },
      {
        "root": "bootstrap",
        "path": "module_public_input_installers.py",
        "bytes": 18820,
        "sha256": "ec9992465a4410199c92428b5a97ffefdeb6d55c0ab9e1152f3a9a956fa6f9ba"
      },
      {
        "root": "bootstrap",
        "path": "native_access_state.py",
        "bytes": 7998,
        "sha256": "f956200a5094bf7c4ad93f75b5b41527a7c9356440069be92eac84b05a6c9277"
      },
      {
        "root": "bootstrap",
        "path": "native_credentials.py",
        "bytes": 13908,
        "sha256": "93f3c940adc135e61012ad7ecfe67bb57eac488c3b68be57e0d98e6df9babb65"
      },
      {
        "root": "bootstrap",
        "path": "terrier_district.py",
        "bytes": 7906,
        "sha256": "c7d3a9215b437a0b8d209d6bedba72fd32016fde052c91b889e1196ba40a3641"
      },
      {
        "root": "bootstrap",
        "path": "terrier_github_snapshot.py",
        "bytes": 8384,
        "sha256": "bcc8c6753a370cca339b47692a1688e53c148909397e69f0f70f9b9e820a4e79"
      },
      {
        "root": "bootstrap",
        "path": "terrier_owner.py",
        "bytes": 4806,
        "sha256": "86a8d731975c0cbbbd00d6f61cae3c980c318d2345b06b64823e85b9ad88caa5"
      },
      {
        "root": "bootstrap",
        "path": "terrier_standalone.py",
        "bytes": 15342,
        "sha256": "077f5936fca26cab3e382d34d6993f452d2b657ba951656362552bbcc4afa8e7"
      },
      {
        "root": "source",
        "path": "mentat/app/access_gate.py",
        "bytes": 18916,
        "sha256": "dc7ef05085044601884ce037f21c1b44d774e7dffba3a0276a3ea5423227e58d"
      },
      {
        "root": "source",
        "path": "mentat/app/access_stats.py",
        "bytes": 14211,
        "sha256": "476450c00af77bba256d41bbec701a360bbc75580d59ab8d3c454d903a446542"
      },
      {
        "root": "source",
        "path": "mentat/app/acu-theme.css",
        "bytes": 6059,
        "sha256": "16dcfb30267299134220d83e7b046a361c74bf0404422ccd3e6aa6609c125d58"
      },
      {
        "root": "source",
        "path": "mentat/app/analysis_data.py",
        "bytes": 39468,
        "sha256": "25e539ba2ae4c7e55e4703a8a17e979d2dc9359ca175fe025bc611dba30928b4"
      },
      {
        "root": "source",
        "path": "mentat/app/analysis_history.py",
        "bytes": 12443,
        "sha256": "f8c3bb575148f3cb7608aed47d3c1dbbf42858be5a8d4d470948a5830f2db5e2"
      },
      {
        "root": "source",
        "path": "mentat/app/analysis_integrations.py",
        "bytes": 39555,
        "sha256": "37ba0dd61344a71b2fb957375f2bdfe39494149abfb6d47b45e90f0c7fd59e6e"
      },
      {
        "root": "source",
        "path": "mentat/app/analysis_metrics.py",
        "bytes": 59861,
        "sha256": "a4777b34152db860bbc992694334d43d57d1375f9a52e4c8dd0c5ac6b6823358"
      },
      {
        "root": "source",
        "path": "mentat/app/analysis_scan.py",
        "bytes": 3087,
        "sha256": "d7a0b992ac67394cca41bd215eafcc2e442433bbe95d16aadc27ce65f39f734b"
      },
      {
        "root": "source",
        "path": "mentat/app/app.js",
        "bytes": 95560,
        "sha256": "e5e6f75613c683a05655a4e6469091b9ded0068fa36c6a024d82fc6fda6a69e3"
      },
      {
        "root": "source",
        "path": "mentat/app/bulk_oppexp.py",
        "bytes": 7555,
        "sha256": "138a2fcd4b6da7b07871800014379bde0112126c3e9441015ef9dc2ced7842d6"
      },
      {
        "root": "source",
        "path": "mentat/app/candidate-spending.js",
        "bytes": 42676,
        "sha256": "e69b17c4fe56ede9aee4681f9f2536e37137b604d49666e76a170b255b877a8f"
      },
      {
        "root": "source",
        "path": "mentat/app/candidate_spending.py",
        "bytes": 46073,
        "sha256": "45dc5be05a38aba9972d1340447d079286f740e4a7ba30e0383ae5678dc28ef1"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-briefing.css",
        "bytes": 7319,
        "sha256": "19af16489ca3cccbe23cf00f86e49cc1f8e76e036cb02e261ffc7062869f2c38"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-briefing.js",
        "bytes": 32102,
        "sha256": "b9e8cb713c9c6dbd9c15b3f5c44189cbd6b6df80d0c066053098bc73829f5974"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-export.js",
        "bytes": 7146,
        "sha256": "efffe0c38a6138d39afd17b8aeebd62d105b6bee9d8100ee1466747cab12e878"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-math.js",
        "bytes": 87255,
        "sha256": "42daf6cca03484505178c2dbce927dd4702738998401ca1cbe9ef55866f1285c"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-studio-contributions.js",
        "bytes": 44915,
        "sha256": "a5318154ae297d4ad9b9afe1a12f490c9e14d02fb61f3de7d1f5686a55346eb9"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-studio-core.js",
        "bytes": 145209,
        "sha256": "269464f37f0b0c53708f8a0203b4eec3fb8696eaf88bc95efb3705f9e77862c0"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-studio.css",
        "bytes": 69487,
        "sha256": "a2bd6f2561c43f629d953918dca910af0d3ef68e62d57ed22236938dfbfc14f0"
      },
      {
        "root": "source",
        "path": "mentat/app/chart-studio.js",
        "bytes": 358969,
        "sha256": "1ef45de0af3b93852f2957e2761dc64b0cd4dcf48cf25e9df1ba51911cd0cfed"
      },
      {
        "root": "source",
        "path": "mentat/app/charts.js",
        "bytes": 73574,
        "sha256": "a81b2c33868d5b282e2f5c1f51a01eb7f13f5fbb74156fc578f9e4707421e39b"
      },
      {
        "root": "source",
        "path": "mentat/app/collection_gaps.py",
        "bytes": 8117,
        "sha256": "31fa251d3540eacebbdcce2c9b637846d63f6ae98a8b8334a5e2b90590f6504d"
      },
      {
        "root": "source",
        "path": "mentat/app/comparison.css",
        "bytes": 2608,
        "sha256": "5e37f936f242d1355067054deb3758abc101f6cd40120f92e225302f02a974f5"
      },
      {
        "root": "source",
        "path": "mentat/app/comparison.js",
        "bytes": 9070,
        "sha256": "9d9308db84897471c67895857f3b2ce525f02fb871c265416a284fd068e23939"
      },
      {
        "root": "source",
        "path": "mentat/app/comparison_data.py",
        "bytes": 11144,
        "sha256": "53afedf25c66e783dc2022ff67bf20b406073fa447345831446a1d295fa86ec0"
      },
      {
        "root": "source",
        "path": "mentat/app/console_page.py",
        "bytes": 5880,
        "sha256": "53392bcc793a215bd9b2829076624f95a3994d2d9999f3659e41fa42985ba86b"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-charts.js",
        "bytes": 32561,
        "sha256": "7e21badcb0af75284a7497e29cbfdfde5febea0afa3ddda16262e179a850bd10"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-map.js",
        "bytes": 24511,
        "sha256": "9fa8140edd1420c0919f9312c65536a9979d9ba28808443d02b1547e22819122"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-plot.js",
        "bytes": 92160,
        "sha256": "59d71c41cc9d2a33d3406a1861eadfddd8f7d8a34406bb2f32055f852287a540"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-studio.css",
        "bytes": 11790,
        "sha256": "6efd944ee2680c9f61de5707f0423029b15346e3917fee17b1b50a9cb0cc9b62"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-studio.html",
        "bytes": 7586,
        "sha256": "fa38ae7eeb772690d2597794c9161377c0cd47166c9b198f19d1ca90ee73ca6c"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution-studio.js",
        "bytes": 40056,
        "sha256": "cd39887c7cc210587c15861d28dd6b970fdee4dac4767599e2ffae9d3bc17c9e"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_data.py",
        "bytes": 55956,
        "sha256": "19da3a5bb94bad16777e99d3101c34c93709647c7eee9a64b4b850087f74175d"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_geo.py",
        "bytes": 15880,
        "sha256": "acaf241b5081fb3524238cfdd950aca85dd5fdff24450e9220715b4bfc5c3e16"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_query.py",
        "bytes": 33041,
        "sha256": "8e311f7d2ba8179defa38ab796aef671412e7139860e0b0a1d3edd793a3a4011"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_query_store.py",
        "bytes": 16836,
        "sha256": "747f919119583dfa1e2fbbd50cee758f51d1890730b569bff02ee5952c38de45"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_semantics.py",
        "bytes": 18130,
        "sha256": "c8338b922bff7362d72ee5a264fa23afe388436f7414d76036e90308d64ac4ff"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_source_guard.py",
        "bytes": 9285,
        "sha256": "fd4adb2366c6e700cdc1d8406091f2832f0548dcbf23f74879a6c8187c46c42a"
      },
      {
        "root": "source",
        "path": "mentat/app/contribution_workbook_guard.py",
        "bytes": 6775,
        "sha256": "587cb2401eae504667b6a368d39e065401ce0a79ac73003105ba281159d2659d"
      },
      {
        "root": "source",
        "path": "mentat/app/coverage-view.js",
        "bytes": 14291,
        "sha256": "3273e10650adb9100583a21ac7fb6b543f9c5d7f7594819e44617551a3dc1e8f"
      },
      {
        "root": "source",
        "path": "mentat/app/cross-reference.css",
        "bytes": 16135,
        "sha256": "729d98ca7e111c1a3e701a88196c3a7b584a91304d18579e32b13a2312258056"
      },
      {
        "root": "source",
        "path": "mentat/app/cross-reference.js",
        "bytes": 36191,
        "sha256": "58cffd0fb744005d4ddef20c731e8d12f00b474c9d3ce27ffadcfbcd9fba7d24"
      },
      {
        "root": "source",
        "path": "mentat/app/cross_reference_data.py",
        "bytes": 15218,
        "sha256": "204b16d7390316606425aedd54d12816bfe6f1b2dbab35adf2c46b44725326f1"
      },
      {
        "root": "source",
        "path": "mentat/app/district_geo.py",
        "bytes": 29205,
        "sha256": "441e485ff34c750113a06d82336f9a5672623223ff8253ccdcc0dc8aa798edb7"
      },
      {
        "root": "source",
        "path": "mentat/app/downstream.py",
        "bytes": 46117,
        "sha256": "6a9a9597d003c4906f9c84241719417dceedabdb61078a37b7e780f6c08a36d2"
      },
      {
        "root": "source",
        "path": "mentat/app/drawer_sidecars.py",
        "bytes": 41667,
        "sha256": "331bf2c9a69977525c05b6b87c6d4c6fe9613ba2719fdbad4ab6fa587f357d2c"
      },
      {
        "root": "source",
        "path": "mentat/app/evidence-flow.js",
        "bytes": 22956,
        "sha256": "c57d040b8186ded7832a00ddafe3cafe0c2c3f19a9d1c9687a741cf14488a430"
      },
      {
        "root": "source",
        "path": "mentat/app/evidence-map.js",
        "bytes": 68841,
        "sha256": "0ac4eb408959c98e3510bf1b2a9ba273817a0ec7da57aeea9ea0bcdee5d84c65"
      },
      {
        "root": "source",
        "path": "mentat/app/evidence.js",
        "bytes": 212069,
        "sha256": "b83c251a816bd57073193692f8a945904e20223ec8da22397aa193c3f2e5453f"
      },
      {
        "root": "source",
        "path": "mentat/app/evidence_csv.py",
        "bytes": 130304,
        "sha256": "d854655dd7c7143db516cd892206547337815b03e00b7cc08aa7ced3d7f50ee8"
      },
      {
        "root": "source",
        "path": "mentat/app/evidence_geo.py",
        "bytes": 89027,
        "sha256": "7cb09ec1aabfd04d58e387d53a626b57e1806c6aaee2fb56ce5741052186091a"
      },
      {
        "root": "source",
        "path": "mentat/app/fec_citation.py",
        "bytes": 16783,
        "sha256": "57c213a3280150048c3ea5a73570555b30ee05a32a44d36f3384ff09076b6641"
      },
      {
        "root": "source",
        "path": "mentat/app/figure-pdf.js",
        "bytes": 19782,
        "sha256": "a7a7fe8f21545bc5feb2a810bbe5751fbdbff5eaff59ddf1dd6ccfd7e263f5c1"
      },
      {
        "root": "source",
        "path": "mentat/app/figure_pdf.py",
        "bytes": 21147,
        "sha256": "ba94fe3ea1fe6b378e0d69c8251864bd1ead4202ea21b60c78c19267a6743409"
      },
      {
        "root": "source",
        "path": "mentat/app/flow-chart.js",
        "bytes": 99420,
        "sha256": "37b8c7aa8d79e0156caa7e3a7c518a3fb33a12580d002935bb4a09c725942263"
      },
      {
        "root": "source",
        "path": "mentat/app/flow-layout.js",
        "bytes": 58534,
        "sha256": "7b35ea63585bd813157febc3640655a2fb53ef3227ef8e5a4042cfaf5ece6fbb"
      },
      {
        "root": "source",
        "path": "mentat/app/flow.css",
        "bytes": 24757,
        "sha256": "2a95f95f842184509b32c9c835f9f3c7f806ca3f8da3b21ff84953f793d7c896"
      },
      {
        "root": "source",
        "path": "mentat/app/flow_data.py",
        "bytes": 148966,
        "sha256": "0f9d7e22b2129ce58d48c981f7532292f2d77b04c6814a0130c345b3a10fd949"
      },
      {
        "root": "source",
        "path": "mentat/app/funding-comparison.js",
        "bytes": 8859,
        "sha256": "86313fbabb552a1977cec47f4f672f102c5749815a827e8b2a369eba1e491f1e"
      },
      {
        "root": "source",
        "path": "mentat/app/geo_lookup.py",
        "bytes": 23147,
        "sha256": "1178f9e476c06926bd63ab1f819f9b82345ddfd4d607e5e4315f666f3688b2f2"
      },
      {
        "root": "source",
        "path": "mentat/app/geocode.py",
        "bytes": 29401,
        "sha256": "7dca8019b2d42641b2a61f8aa38ad6ac3c93ce921dbe36faa640151fa15b88fc"
      },
      {
        "root": "source",
        "path": "mentat/app/giving-forecast.css",
        "bytes": 34045,
        "sha256": "84a9ff27c0b0f0552b016ec50158fa3c36d12acc64fd36d0222488bbec21e02f"
      },
      {
        "root": "source",
        "path": "mentat/app/giving-forecast.js",
        "bytes": 196131,
        "sha256": "7be37c9a27c3bdaaf0570f0a7f87490a26a560eb8af7635cf75e827140929b0d"
      },
      {
        "root": "source",
        "path": "mentat/app/giving_forecast.py",
        "bytes": 146477,
        "sha256": "a5154fa6de46b16ecec1bad6df0b860d601be28318b136a3cc2445a3415e146a"
      },
      {
        "root": "source",
        "path": "mentat/app/glassbox_emit.py",
        "bytes": 4103,
        "sha256": "8eb2b0d76a1ce308f695739082d6c54faacd601a1fd8fc6c7148318614c0f0a9"
      },
      {
        "root": "source",
        "path": "mentat/app/graph-explorer.js",
        "bytes": 11834,
        "sha256": "49815337626634fee9b45a8d94b097466f40d8eaecde990414a19ea283a39111"
      },
      {
        "root": "source",
        "path": "mentat/app/graph-flow.js",
        "bytes": 20554,
        "sha256": "f65a1a491c6cd103b3e230638f3b15c1b441cce731b6e76d4030d15c3525c135"
      },
      {
        "root": "source",
        "path": "mentat/app/graph.css",
        "bytes": 73676,
        "sha256": "6a73f9a5139d614523f8a210e331d9c8c131c5675291fc77584f79fe04306236"
      },
      {
        "root": "source",
        "path": "mentat/app/graph.js",
        "bytes": 233755,
        "sha256": "090c6a44dc12bbe380870166f87e18b74fc11ca68b1ebe775edc9820e618cf67"
      },
      {
        "root": "source",
        "path": "mentat/app/graph_data.py",
        "bytes": 83391,
        "sha256": "558b84314bddefb440bd5b577331cab65bcecc51d62c73d310695499501b6ea9"
      },
      {
        "root": "source",
        "path": "mentat/app/grouped-chart.js",
        "bytes": 12389,
        "sha256": "614db225e6b4c5d889b5bac89f294c7b72b1df6b9efd04a0c73ee0ddcfeb3b71"
      },
      {
        "root": "source",
        "path": "mentat/app/index.html",
        "bytes": 107064,
        "sha256": "eedede73d24b1df0c3b52175b24189bc86607be0a19fd4b5a506e48f4da29ca0"
      },
      {
        "root": "source",
        "path": "mentat/app/industry_scope.py",
        "bytes": 5158,
        "sha256": "9ac2672daaf4bd2f354609bc6745d2ea2bdfd39e2721522647cdbaf340ae2bb1"
      },
      {
        "root": "source",
        "path": "mentat/app/insights.css",
        "bytes": 27129,
        "sha256": "a04c658a158052ce03f90554019b7d91ea6f948093b6ee6b575e01ed3efd7312"
      },
      {
        "root": "source",
        "path": "mentat/app/insights.js",
        "bytes": 98585,
        "sha256": "6f451bfab76d2e9731fd294310cf6297c7853260b85f474f726b1c77c441246d"
      },
      {
        "root": "source",
        "path": "mentat/app/map-engine.js",
        "bytes": 67234,
        "sha256": "84d0cfa2f7bbba7312c38d66488b0e0953abaf560c9718cbe79a22197bdcaf41"
      },
      {
        "root": "source",
        "path": "mentat/app/map-evidence.js",
        "bytes": 34366,
        "sha256": "c9f905645aefb1c8879de96993e9bded278af2c6ed9cc7a5154c988df8f7e9d9"
      },
      {
        "root": "source",
        "path": "mentat/app/map-layers.js",
        "bytes": 69906,
        "sha256": "5979255c3e3ca7bb3e912076c613bb7dadb2a08008ef142ab9cfcbe80456321f"
      },
      {
        "root": "source",
        "path": "mentat/app/map-studio.js",
        "bytes": 71177,
        "sha256": "b4ec1ce11e6d43ff575d5ea9f8a0ed70073082eb98d19650ec71ed05fada691f"
      },
      {
        "root": "source",
        "path": "mentat/app/map.css",
        "bytes": 35128,
        "sha256": "774c42c1e3acf18022e03a103acb9ff896947376d63ba37e825dee24226c878f"
      },
      {
        "root": "source",
        "path": "mentat/app/native_scan.py",
        "bytes": 5452,
        "sha256": "efd96248d0c5e20b7661dd0fac3d89bba7c7b7e3def01a634d1e3139eedf2a5a"
      },
      {
        "root": "source",
        "path": "mentat/app/pac-giving-forecast.css",
        "bytes": 5367,
        "sha256": "e0cfe162f05ad17dc4dc7c864dd00345dc896c7594d916511bf8d16954e31026"
      },
      {
        "root": "source",
        "path": "mentat/app/pac-giving-forecast.js",
        "bytes": 293191,
        "sha256": "1d1d80b118ad3ed4be105b5aaf2d879790f72352e263904357f6a10b5dad3d44"
      },
      {
        "root": "source",
        "path": "mentat/app/pac_flow_access.py",
        "bytes": 6460,
        "sha256": "e4ecd0d25c14f67139c06a5b0489bd6098974e1d0262a478d459a81caf0f8c6d"
      },
      {
        "root": "source",
        "path": "mentat/app/pac_giving_forecast.py",
        "bytes": 16267,
        "sha256": "a9578544f74f8786712e0d08f7b122b0043547fb7a21e1786187c068dcc84cd3"
      },
      {
        "root": "source",
        "path": "mentat/app/partisan_political_forecast.py",
        "bytes": 16105,
        "sha256": "9fe3415fd43b034603e216b2515699071bf7e5f4e84a7693c076361bd7a8596e"
      },
      {
        "root": "source",
        "path": "mentat/app/prewarm.py",
        "bytes": 220578,
        "sha256": "a880a5d598e9766a5fd4a747876eb5a36c2ad3845b2193822f624a73c3ca26e1"
      },
      {
        "root": "source",
        "path": "mentat/app/proclock.py",
        "bytes": 30944,
        "sha256": "5211dbca972d123a957f6a43652bb2964aaaebfeed76ccb30f3ab36efcdf0577"
      },
      {
        "root": "source",
        "path": "mentat/app/public_data.js",
        "bytes": 6512,
        "sha256": "720ce355507fd63528642475e02b10e559b56b713f185b6dc8495dcf1163cb1e"
      },
      {
        "root": "source",
        "path": "mentat/app/public_data.py",
        "bytes": 16175,
        "sha256": "3d02835f2e8c23d96f668b045fa5aa08e92d67f0aef350dd3c71327ef3626bef"
      },
      {
        "root": "source",
        "path": "mentat/app/python_child.py",
        "bytes": 2584,
        "sha256": "ea3de49d684ab562f6c07a63f960ac7a14baba8b93a7aa0dbb2e625871c1e246"
      },
      {
        "root": "source",
        "path": "mentat/app/receipt_path.py",
        "bytes": 1616,
        "sha256": "af6e20881fab06edeefac36b0ba24e54d10cdc855a13b487da7bcf9e15d194f6"
      },
      {
        "root": "source",
        "path": "mentat/app/records_sidecar.py",
        "bytes": 15897,
        "sha256": "e0a46e89e0d5f22cc1dab303222bbcd045f8c3ec2bae57279fc83f57560f0ef3"
      },
      {
        "root": "source",
        "path": "mentat/app/report_identity.py",
        "bytes": 1006,
        "sha256": "1547e5eff337248274725f7ff36f163f8c6d8be93029d94cfb7f0868ea5149eb"
      },
      {
        "root": "source",
        "path": "mentat/app/report_insights.py",
        "bytes": 34644,
        "sha256": "33348dc6bb5a34fc8894afa427081d94bd6c2d6d7d5a56a70555007266542ff6"
      },
      {
        "root": "source",
        "path": "mentat/app/report_publication.py",
        "bytes": 13414,
        "sha256": "e7fa539b08871fb944e594404b86934a90940714c447f059ec36c0f80c2bfcf6"
      },
      {
        "root": "source",
        "path": "mentat/app/response_cache.py",
        "bytes": 40455,
        "sha256": "393a5cb7470997a0ac4ac30e10e5e05d44f538a998b29e6de5b04d0918ebf2e2"
      },
      {
        "root": "source",
        "path": "mentat/app/runtime_paths.py",
        "bytes": 6851,
        "sha256": "777159ac4b4aab4029a324c96f23a962f9efdde84df4fe2d0eca6748da01421e"
      },
      {
        "root": "source",
        "path": "mentat/app/scope.js",
        "bytes": 20109,
        "sha256": "086e8cff4c9d155efd8671f3149a617477d0b05d47ecc37b60509af68f7de547"
      },
      {
        "root": "source",
        "path": "mentat/app/server.py",
        "bytes": 231271,
        "sha256": "78dd33b88e1ce45828bf71044d32f4788051576c0ed3593e4e6e71bb92ae42fa"
      },
      {
        "root": "source",
        "path": "mentat/app/snapshot_registry.py",
        "bytes": 12468,
        "sha256": "7b1719076f424230d73c8291a4e8bafdf1fe34e26ac44b49d1ed737250b38371"
      },
      {
        "root": "source",
        "path": "mentat/app/source_memo.py",
        "bytes": 10365,
        "sha256": "54e39fb21a481d28a9bf566bb84af9a7da4451962d4d1d5998466022bfadcad7"
      },
      {
        "root": "source",
        "path": "mentat/app/studio-flow.js",
        "bytes": 38624,
        "sha256": "b313e7d69765590f600d6ff15119d87639ccb7d90949ce379681a1c2db4bbb9c"
      },
      {
        "root": "source",
        "path": "mentat/app/style.css",
        "bytes": 69568,
        "sha256": "2e5f7646ef32ed937699aa60b34eee26bee9f0e51a2f6f35f8b8dc5d043525f6"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/index.html.j2",
        "bytes": 1051,
        "sha256": "2208cd1f514628572aa747bc6725b0a53c4b4d711e0a4d8adc71c0447e8c9d32"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/page_head.html",
        "bytes": 2493,
        "sha256": "04b53dd34c2de7fe4bffe12390d3b916aeee583fb444fd56abadbd13976edb43"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/page_shell.html",
        "bytes": 2461,
        "sha256": "2192c9e001ac97c67dd240c4315e5147f5e83f875b2cfd4deb0238a5763ac4e0"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/page_tail.html",
        "bytes": 156,
        "sha256": "41d725c9cf4af2fbd69514d6f378181b8ec76ddb3fde7da7a9fcf189672b2c38"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_chart_studio.html",
        "bytes": 29474,
        "sha256": "82f09686c656a52a06586502dc26d5a6801ca58ee6216fb3e5bb55f96282b9cb"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_collection.html",
        "bytes": 9231,
        "sha256": "e441d30d6c2b9365ee37443fbc92ce107a2adf2b272e9ba0bea63fab98b2136a"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_cross_reference.html",
        "bytes": 821,
        "sha256": "44e829541813104ff1942971b60b401f961cb37c31dfac8aa0bc34c748a98a7f"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_evidence.html",
        "bytes": 5857,
        "sha256": "2cf20d29358f2aca13fcf4f640fc88435a23407e1a163eec80768fbc28721cbd"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_graph.html",
        "bytes": 32223,
        "sha256": "9a000ed5b3af942079e56260791296c2c96cc4832c2fa54f6b22ca1786501af4"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_insights.html",
        "bytes": 14686,
        "sha256": "761c85c2c179e777bf9ac4cbc064237a8118f165616a4dc3be4f36db78e54a2c"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_loading.html",
        "bytes": 8440,
        "sha256": "8bba3f6360910088bf01a63659be5764be5e45b6e4e6723dc3fc333b137f7389"
      },
      {
        "root": "source",
        "path": "mentat/app/templates/view_public_data.html",
        "bytes": 1222,
        "sha256": "bc7f1bdf338fca286f4fa7a80f0b2e220189051ef08a6b653c4df84f4af168be"
      },
      {
        "root": "source",
        "path": "mentat/app/theme.js",
        "bytes": 10541,
        "sha256": "1ba2f9ba85b418babfdad895747b5afa13ce9acdb50e2137d92b02b326fa7a32"
      },
      {
        "root": "source",
        "path": "mentat/app/ui-state.js",
        "bytes": 3327,
        "sha256": "a0782725221c5dadc4a932dedc47fd431fd33a724e1ffde7ff70bad1a6a0c860"
      },
      {
        "root": "source",
        "path": "mentat/app/vendor/pptxgen.bundle.js",
        "bytes": 460889,
        "sha256": "4fb9eac5cfefb213e2d8743c2b7151025f31bfb3f834c73c12062916daa0f3f8"
      },
      {
        "root": "source",
        "path": "mentat/app/view_cache.py",
        "bytes": 8331,
        "sha256": "e7ea1ece7fc9d3f46b051a868ec75c463400322798813ff45d2e33cf60addcd6"
      },
      {
        "root": "source",
        "path": "mentat/app/worksheet-comparison.js",
        "bytes": 11147,
        "sha256": "f0548ca74e66d8bbc9e19757ff401cafe70693ead0867be419940ed42cb42085"
      },
      {
        "root": "source",
        "path": "mentat/app/workspace-polish.css",
        "bytes": 86511,
        "sha256": "9975d64541013b29928d390e85ea8260229d7a74ac4d8745a3b9eee98de88117"
      },
      {
        "root": "source",
        "path": "mentat/app/workspace.css",
        "bytes": 117754,
        "sha256": "64f6a5981d6671414cbeb263630753207b05ed3f96a62dce51ada5bbd6ff67dd"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/build_giving_anchors.py",
        "bytes": 38536,
        "sha256": "e7f39f79c4e98f3a984c0a989eaab654ced87f793ceb5ce701e1612cbec2ebe1"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/build_panel_cohort_split.py",
        "bytes": 7062,
        "sha256": "12b4cd6f71f61c23dd9b34282e32f6c901e35263b08be83c1f0cf4b12d1ba9b6"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/coverage.py",
        "bytes": 2440,
        "sha256": "7964e8fa158430e9a33ae9255f92c474d48e77b63944de6f010cbde8615e03bf"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/cpi.py",
        "bytes": 1487,
        "sha256": "e31f39e2bca8132b462ea6c6488c60498c874c1b48b5c8d2d74496af5d5b1e41"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/d049.py",
        "bytes": 6270,
        "sha256": "1302d0c3943a72787536fabe75f57e8a73d8863545803f8d3fea732e5b6233d9"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/fec_pas2.py",
        "bytes": 7108,
        "sha256": "8f1aa1a08280b55cde1e08aa4e0cc6eaf22543e1c43532a612f6ed86b4ad0860"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/glassbox.py",
        "bytes": 5040,
        "sha256": "1c9cb394ecbe7c98cb1b0e68c8b9d0c09d655306be818ff42b55d4257ae122db"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/lda.py",
        "bytes": 8464,
        "sha256": "a17ba0a6a1e612a9fd437f9652b68625325efc979109324d29a2cb168909f865"
      },
      {
        "root": "source",
        "path": "mentat/forecast/anchors/mentat_sources.py",
        "bytes": 15743,
        "sha256": "5f95c29c60edd9f6041724ff60595ced60ebdcc76b5f1dba57bed1f4417596ed"
      },
      {
        "root": "source",
        "path": "mentat/forecast/contracts/contract.py",
        "bytes": 24959,
        "sha256": "85c7d4550cba7e8314f0c4f74eab9c6cd31306d1cf33cb76a5eafca4fa978ed9"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/baseline_refinement.py",
        "bytes": 14468,
        "sha256": "265f69c2b1ca38c6ee73c7a7336b7da3797a9692fcdf10dd62065733bb049eff"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/bounded_pac.py",
        "bytes": 29183,
        "sha256": "4de4b01193b0230bd9ae8d01d7ee8105e72061f3b21caf01f329f677a0168793"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/build_political_bundle.py",
        "bytes": 5587,
        "sha256": "f0f57769389d72909f0d4290cdaa8c348088db4d66ee1ae9be134965899a5d7f"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/build_refined_baseline.py",
        "bytes": 6588,
        "sha256": "067ac62c3e563a8a2553ddb2ff8d4d99b2c1ccbaa6e8b6eda1f3946aea9ab5ef"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/calibrated_baseline.py",
        "bytes": 11485,
        "sha256": "2ca4477410ec01e65cf91e0960497b50bc773a722a084445d3603cf02ebe3e99"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/evaluate.py",
        "bytes": 23424,
        "sha256": "8f83ab0d1003740b092bf2fc02817ab5e29fd9c09f496d04b68aef01cf7d7133"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/evaluate_political.py",
        "bytes": 3297,
        "sha256": "103be82e04a215391e963fb197dbf874da7f6b76fb3af75ecd68d0ec0f45a50a"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/fit_political.py",
        "bytes": 9994,
        "sha256": "38a9815bba3e1d1f027ef966370897ca0f7e33f8709a4b8bd3fcb9566a9b7859"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/guarded_baseline.py",
        "bytes": 7638,
        "sha256": "e9a9ee1aea8bd5e9655156ca79a13ae02e13b84b2f0ef9c22bb901911ee7df1f"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/pac_nowcast.py",
        "bytes": 19678,
        "sha256": "9e3529bf1bf4b8ed78ecef4bd3c5a68082eaff8f77ffab2f71b689561f206562"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/plot_bounded_results.py",
        "bytes": 3807,
        "sha256": "12a3be771cf1c8c5bd216679354181368143bab18b9dd9fb93de5cc878f30f83"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/plot_political_results.py",
        "bytes": 2806,
        "sha256": "9e428917dae4fb2382eb4351017db32de49f64fda04eef28f63700caedd6a8fe"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/political_features.py",
        "bytes": 10110,
        "sha256": "e263db8b7ca8932d1e078930db5db8c72c1f75c4d7b5765aabc0ab9ba3ddc808"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/predict_interval.py",
        "bytes": 20352,
        "sha256": "94ec735c97c94e6c12481f31d15e35781acd1d4100920d4e77aafc07d850258e"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/publish_refined_baseline.py",
        "bytes": 2323,
        "sha256": "4411ae56b1c33113c084044f8e70c8ebc319fc2596201a8a26308b9696d4dac6"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/run_baseline_refinement.py",
        "bytes": 2213,
        "sha256": "97805b59010dcab76c1ecde4947af89c9cfaeae4c5a29a4d8a46f23d6489dc94"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/run_calibrated_baseline.py",
        "bytes": 2264,
        "sha256": "1bf70cabe8926709e2142611ea950abd89a4de8698ac673d93fb0ce17bf1a02d"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/run_guarded_baseline.py",
        "bytes": 2045,
        "sha256": "0dc3d037a6acaeb58836553e9dff32b8c93c84e3200431c0349599ea68c3d2d1"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/verify_bounded_results.py",
        "bytes": 8951,
        "sha256": "f7d95a22e3d0b494f8b395871063c808e86edee308be731245a1b79e334804fb"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_dollars/verify_results.py",
        "bytes": 18325,
        "sha256": "1ef762b1c3f5d3e55adc3ceef3eee2591e7701c65e07a500142550f2e400e333"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_refinement/evaluate.py",
        "bytes": 29868,
        "sha256": "b8831aa06ce6fd32e96fb44bb0330171b907ad2c71005ca1d7f0756d68a7e61b"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_refinement/predict.py",
        "bytes": 23050,
        "sha256": "dd0ebcb3686561c3d0a805d3a17877cca30729606dfa137f41194f5600b66730"
      },
      {
        "root": "source",
        "path": "mentat/forecast/partisan_refinement/verify_results.py",
        "bytes": 7810,
        "sha256": "6dcda0948e19fcf3c128f979d5dc8a20a0c2dad54812335ad7780e41f9a65e54"
      },
      {
        "root": "source",
        "path": "mentat/forecast/refit/tools/check_bundle_contract.py",
        "bytes": 2280,
        "sha256": "9c4b77c68dca88d87bdbc7bdcc5bacce111f77e38fbcebd6cef420e489c0c195"
      },
      {
        "root": "source",
        "path": "mentat/forecast/refit/tools/g8_consumer_smoke.py",
        "bytes": 6108,
        "sha256": "532e26be1a7cbea62b409509a33fea90200f003c687eb978bd8bb7d87d7b8361"
      },
      {
        "root": "source",
        "path": "mentat/tools/api_company_cycle_fanout.py",
        "bytes": 91108,
        "sha256": "ecb2ec3327b9ff43a69f72fa93934c4b05b04ba990ec4837aaa37c6325faa3ac"
      },
      {
        "root": "source",
        "path": "mentat/tools/api_host_pool.py",
        "bytes": 35861,
        "sha256": "7f7ae80561814f6b0c8eb25cb93091d6a6ce575ab8fb251335a1accf7aa2048e"
      },
      {
        "root": "source",
        "path": "mentat/tools/api_request_budget.py",
        "bytes": 8901,
        "sha256": "451ae8a8445baac600a046ce0284a21a09e1309e192a86d5b7fa4438cdee9ee3"
      },
      {
        "root": "source",
        "path": "mentat/tools/api_request_pool.py",
        "bytes": 31094,
        "sha256": "2251f236230961ef0922a37c4a90e0afa451efbe6a6a47206a0ddcc0a012f131"
      },
      {
        "root": "source",
        "path": "mentat/tools/archive_cassette.py",
        "bytes": 6480,
        "sha256": "9501d77f96b84671eb84ae8581bef897542696d5f6b40fecfb569ed0b65105ca"
      },
      {
        "root": "source",
        "path": "mentat/tools/arrival_gates.py",
        "bytes": 8334,
        "sha256": "618f984b305ac14661fe1ce96bcdfc10927467005327f54f55f33ff70ca366d1"
      },
      {
        "root": "source",
        "path": "mentat/tools/attribution_policy.py",
        "bytes": 1101,
        "sha256": "b1ad33a0c868ffc8de00c2f811af45ca2d206fa1b407e494227616d1da7dae60"
      },
      {
        "root": "source",
        "path": "mentat/tools/audit_collection_outputs.py",
        "bytes": 13788,
        "sha256": "da31b2f8fb43d240d35bb904d795277f4467779c869e365f16c831e92ebe3bab"
      },
      {
        "root": "source",
        "path": "mentat/tools/backfill_contributor_street.py",
        "bytes": 12620,
        "sha256": "cc0d1d8791db3a6030994c2e0aa67bac0849f5f3621102ec8a74ea0a296b3f66"
      },
      {
        "root": "source",
        "path": "mentat/tools/benchmark_native_ui.py",
        "bytes": 3966,
        "sha256": "186a15369464765a461be20a160bcd514c4a24e7de47382b8b0d1ee3216cb056"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_attribution_report.py",
        "bytes": 4355,
        "sha256": "d0dfb5436a9b3ade3f7f921c08a3c4e1e0334f4644c83b66109081d1d52f53d8"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_bulk_activity_index.py",
        "bytes": 14692,
        "sha256": "ec243c977357637973fd099c37792e3f5edee0be951a5eb2a6e3fc181759561e"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_district_geo.py",
        "bytes": 46324,
        "sha256": "5503168125228feacae1fe9b995fc049eac15648c4fb276df504f2c658660f51"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_geo_layers.py",
        "bytes": 76849,
        "sha256": "627aa8d74d39a598b12c620a9f9be339cfbd2ae32abc6bbedd771c019b2f6c31"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_giving_models.py",
        "bytes": 8307,
        "sha256": "4aebc96ec714c045f3a43c2278af984fcc03b17707f37bf69a039cbd5ee4a29c"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_state_legislative_geo.py",
        "bytes": 25034,
        "sha256": "9b14fd1e8b8b2e5a37a58f287b153d798207f8f68161d3e7118e5a072bac0c9e"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_tidy_workbook.py",
        "bytes": 61653,
        "sha256": "12a245afb848974dd241237373ad058edb1ae0ecf2790bf1a582561ae1077e35"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_tract_geo.py",
        "bytes": 7566,
        "sha256": "b0f1cf6149b0c3d237ee3ec823e6fcb70bb7c6c472f14d26ce2292271cf548d3"
      },
      {
        "root": "source",
        "path": "mentat/tools/build_zip_centroids.py",
        "bytes": 17945,
        "sha256": "5761b67daf84f5b287c18e5b00506f6a304504e772f6767a4777a3a3e257c5c8"
      },
      {
        "root": "source",
        "path": "mentat/tools/collect_committee_activity.py",
        "bytes": 129912,
        "sha256": "342cf16c3bb4f5e3a2634c24d53873e885efe4f9b4d031e2674580f919bc2e25"
      },
      {
        "root": "source",
        "path": "mentat/tools/collection_coverage.py",
        "bytes": 15153,
        "sha256": "c0a0b2edcebe90187289fbd0ed50865f5c4805289fd4d67068193b78e9ca055b"
      },
      {
        "root": "source",
        "path": "mentat/tools/committee_activity_reader.py",
        "bytes": 14001,
        "sha256": "a7760ddfdea216e1fded8ac51ebd0ced62692dc60cf30dd78f1d9da4a27cd662"
      },
      {
        "root": "source",
        "path": "mentat/tools/compute_job.py",
        "bytes": 37102,
        "sha256": "46238ba211b91a7b456d91618140c19cf33d90685ac61ed6d73e7548cfbf4716"
      },
      {
        "root": "source",
        "path": "mentat/tools/compute_parity.py",
        "bytes": 11366,
        "sha256": "48e5ebcc4b9933a214591749f1ba09aff8d7c12d3f9457f121f0135572fe8fea"
      },
      {
        "root": "source",
        "path": "mentat/tools/compute_secrets.py",
        "bytes": 5079,
        "sha256": "bc4bf9e07c40c1f0ee3830f8a5dbdab4b76156b012c8b180ce131c77b97c185b"
      },
      {
        "root": "source",
        "path": "mentat/tools/cross_reference_digest.py",
        "bytes": 23670,
        "sha256": "4b89bab6aa32f49f7c869aba59719329f456f95134fd12fee54e6d36d75cfa7e"
      },
      {
        "root": "source",
        "path": "mentat/tools/cross_reference_engine.py",
        "bytes": 50313,
        "sha256": "7bd2bdaa9f8951cbc1456b03ba0bb49a95e32a23fb92224c68809856a1ac47bb"
      },
      {
        "root": "source",
        "path": "mentat/tools/cross_reference_store.py",
        "bytes": 30845,
        "sha256": "d687f488e481314f594f0a288a8a4a0281f6884ba6639817389d7b104b03c09f"
      },
      {
        "root": "source",
        "path": "mentat/tools/downstream_volume.py",
        "bytes": 23164,
        "sha256": "45b511cc9b060a8f4d6933671671d86b1d40963b8219bc9017de42deda106f7b"
      },
      {
        "root": "source",
        "path": "mentat/tools/enrich_downstream.py",
        "bytes": 34688,
        "sha256": "7dd058cfe68c7d59efdaafeeb1343e37a6766c0f27cae6ac912c78d1c348d5f8"
      },
      {
        "root": "source",
        "path": "mentat/tools/export_raw_contribution_warehouse.py",
        "bytes": 42259,
        "sha256": "4ab775e4826e98e4e5d846d7b69ca25117926d0f0da3fa5dde5cc80a9c1d100e"
      },
      {
        "root": "source",
        "path": "mentat/tools/fec_accounted_client.py",
        "bytes": 15990,
        "sha256": "fe5dfa45256d883e293392c67e82f2a83bae191a72999fc1c9119f1de3e02166"
      },
      {
        "root": "source",
        "path": "mentat/tools/fec_filing_headers.py",
        "bytes": 8509,
        "sha256": "30766fc320fdb7d7d7ee13e78eaffc59114393c7571a381efa6a5325f9a35cd8"
      },
      {
        "root": "source",
        "path": "mentat/tools/fec_key_store.py",
        "bytes": 8039,
        "sha256": "d8c84039d367875c135a7e5195d64fadf591f2db0a83a9f4125ec963361fe23f"
      },
      {
        "root": "source",
        "path": "mentat/tools/fec_transfer_graph.py",
        "bytes": 35032,
        "sha256": "7e058a55f992e21bf5d6b1c818f009220af6b6c01793835df9b83a34ac00e919"
      },
      {
        "root": "source",
        "path": "mentat/tools/geo_assign.py",
        "bytes": 47360,
        "sha256": "93cbe4a02ab62ade491757e0e97a2d28db40b2a8aafb93e0369b152018822041"
      },
      {
        "root": "source",
        "path": "mentat/tools/hydrate_receipt_metadata.py",
        "bytes": 10926,
        "sha256": "e37b45174403fed1f264cb1d16bb90a3f92d792ba7f4b234603d342c053853d9"
      },
      {
        "root": "source",
        "path": "mentat/tools/mentat_env.py",
        "bytes": 1144,
        "sha256": "8f5a4376b7e10e75e0ede09538894388e65ad51880d4cad8993ccc2b9bf7d323"
      },
      {
        "root": "source",
        "path": "mentat/tools/merge_company_shards.py",
        "bytes": 64126,
        "sha256": "e2890317ab3e84a13ba91bf78aa58b689d5acd2939f5761a4195f4ae2dcdc6f9"
      },
      {
        "root": "source",
        "path": "mentat/tools/origin_closure.py",
        "bytes": 12646,
        "sha256": "1b68364dd93fb154e3bfb6268f0ed55bbb1fdb8008d50a355aa2b50f20fe2503"
      },
      {
        "root": "source",
        "path": "mentat/tools/original_giving_experiment.py",
        "bytes": 8147,
        "sha256": "e82467123669b54ed6b83dbacb684db1a5e466636a71b87dc9bc43ff76d2b6d0"
      },
      {
        "root": "source",
        "path": "mentat/tools/pac_cash_model.py",
        "bytes": 20847,
        "sha256": "01f8e3f4c1d72e7803b0073d746276fcec44d627bcb156adc3d3a5b94cc87eaa"
      },
      {
        "root": "source",
        "path": "mentat/tools/pac_evidence.py",
        "bytes": 37460,
        "sha256": "291fe14702229207c8dd7bf4adaabc9a9424c0c6b2e2a8c6822caf4b8f8e5b43"
      },
      {
        "root": "source",
        "path": "mentat/tools/pocket/build_page.py",
        "bytes": 2150,
        "sha256": "ed09156adea5fd30e6064182df0f8d5a719a92f14a087bca035fba9ed5d0315b"
      },
      {
        "root": "source",
        "path": "mentat/tools/pocket/extract_pocket_data.py",
        "bytes": 17938,
        "sha256": "2e3a1db16cf56bb1aaff0b4e68a37ed374a75d9f24f61f520a26c5192fc0cfb0"
      },
      {
        "root": "source",
        "path": "mentat/tools/pocket/negative_control.py",
        "bytes": 5430,
        "sha256": "330f63c3628ee9d1e56352fb46a1fa92303aac5b39ce98f51d476b9c848f3737"
      },
      {
        "root": "source",
        "path": "mentat/tools/pocket/selfcheck.py",
        "bytes": 16772,
        "sha256": "b73453e6372e0e0397d4bb6d097f810c3128ae2d2a0a970365f7324a6b594b5f"
      },
      {
        "root": "source",
        "path": "mentat/tools/prepare_workbook_payload.py",
        "bytes": 3328,
        "sha256": "b1ac5c4aebf2aa04db60b3558df3553a07d54d5f407ae2a5dd3749f6fcdbacd4"
      },
      {
        "root": "source",
        "path": "mentat/tools/publish_report_generation.py",
        "bytes": 879,
        "sha256": "61f3310780be79ba8146b982a4c40f9d73b9ad40a52b0b9dd73b3990fb061fe0"
      },
      {
        "root": "source",
        "path": "mentat/tools/publish_snapshot_lineage.py",
        "bytes": 5512,
        "sha256": "87af548d3e90151f6f631495f3d577c12448be9c1962709ccde966fbdf5e9dff"
      },
      {
        "root": "source",
        "path": "mentat/tools/recheck_attribution.py",
        "bytes": 6237,
        "sha256": "0d99a2454bf33d3503a0093677212d87afaacc917e8aaa356dc45cb14a523c40"
      },
      {
        "root": "source",
        "path": "mentat/tools/recover_filing_forms.py",
        "bytes": 3431,
        "sha256": "cfcdb85d9989b5a07301d4873d5e45e3dbdab522094cf061c4b4348d02bf73a0"
      },
      {
        "root": "source",
        "path": "mentat/tools/refresh_fec_sources.py",
        "bytes": 6269,
        "sha256": "80420ed94f58e8a103951dcc097e94280304580349573b3e5fec28f3b6dc4ec2"
      },
      {
        "root": "source",
        "path": "mentat/tools/render_console.py",
        "bytes": 2873,
        "sha256": "bca9909d713243d5bc586155200f62d6c6d319633213d02ef9fb38c8c079c638"
      },
      {
        "root": "source",
        "path": "mentat/tools/replay_downstream.py",
        "bytes": 4562,
        "sha256": "332f781e80196aebf6154251399c4e946b0c07f654df6ac128d4292d7ff2d1e9"
      },
      {
        "root": "source",
        "path": "mentat/tools/replay_parity.py",
        "bytes": 32043,
        "sha256": "45d4709dcd16f05abae1b17ba829c9ace7437f5345bb7044ccfabf6741f36b71"
      },
      {
        "root": "source",
        "path": "mentat/tools/replay_proxy.py",
        "bytes": 11833,
        "sha256": "d3ba2e7122bfdd361e6b9162939e76061c713417eb50b585e0fff39200917f9c"
      },
      {
        "root": "source",
        "path": "mentat/tools/report_directory.py",
        "bytes": 2236,
        "sha256": "4786da0a3e1027e7945cf8a7ec2f17cf3a90db5b5586b9f419d95c27411b4856"
      },
      {
        "root": "source",
        "path": "mentat/tools/report_source_guard.py",
        "bytes": 19628,
        "sha256": "c20eee34ff1e177b2f9ec1a2a0e621dbbe758bc0d6ec193fd8d2ca9db5908ac5"
      },
      {
        "root": "source",
        "path": "mentat/tools/run_cross_reference.py",
        "bytes": 41900,
        "sha256": "7f0c5fd59a088e2b40baa4224d67d50fb2142c36cbbb0458f7a7e003fbc2ce32"
      },
      {
        "root": "source",
        "path": "mentat/tools/runtime_inputs.py",
        "bytes": 3776,
        "sha256": "896eabaf2851bb1b1bf708d510bbbde13108a47ade534ee71c198edf1513772d"
      },
      {
        "root": "source",
        "path": "mentat/tools/spending_endpoint_contracts.py",
        "bytes": 28339,
        "sha256": "846d8b61d0097d6e48b6d78a4426886675d7fac0838baedefe4331786af69418"
      },
      {
        "root": "source",
        "path": "mentat/tools/split_telecom_workbook.py",
        "bytes": 11327,
        "sha256": "49e692cc7e864e8591c6f28e8ad817463b52dca5294f8c072d2804d20f641432"
      },
      {
        "root": "source",
        "path": "mentat/tools/sqlite_snapshot.py",
        "bytes": 4236,
        "sha256": "5d85966363fb10fc367ca96b34aac5a764ae5a513ffda1456b0f18c4d8d62563"
      },
      {
        "root": "source",
        "path": "mentat/tools/stored_paths.py",
        "bytes": 4006,
        "sha256": "47aacef366ada764941f92d559d206f20d7e67bc62517005fa2473d75fcb564e"
      },
      {
        "root": "source",
        "path": "mentat/tools/transfer_rule.py",
        "bytes": 8795,
        "sha256": "2a21893ca591566680ce92958a4c619ead8e8ce1dd58f0fbb0d8a093e6b1d4c5"
      },
      {
        "root": "source",
        "path": "mentat/tools/validate_industry_coverage.py",
        "bytes": 27972,
        "sha256": "d3be009061a3790be2706d7579d53b044a9bf3fbed1988d07069a0c52a97f592"
      },
      {
        "root": "source",
        "path": "mentat/tools/validate_report_json.py",
        "bytes": 246,
        "sha256": "b6d83764706951775721546ec906dd71f901d71f5b7c6619141998d4078a6d15"
      },
      {
        "root": "source",
        "path": "mentat/tools/verify_attribution_report.py",
        "bytes": 5037,
        "sha256": "90a38c962334e3119ccf1d6690c0cb338933b55ffa8ce41bc9d5ca7d1a7b4626"
      },
      {
        "root": "source",
        "path": "mentat/tools/verify_fec_date_coverage.py",
        "bytes": 9863,
        "sha256": "0e7dd8e21fdf9cafb777b1e625ae0a401fcdc30bf2e480e5b9de9dab5a70fa4e"
      },
      {
        "root": "source",
        "path": "mentat/tools/verify_repaired_reports.py",
        "bytes": 7286,
        "sha256": "6fce3dfdd79aade6647d32ada333c22eecb2e293bc33d54a834186a12cf7a8dc"
      },
      {
        "root": "source",
        "path": "mentat/tools/xlsx_spec_writer.py",
        "bytes": 9876,
        "sha256": "85725351bf3c05a1958bccff40df7d0d9c4277b82f1327e02ec2210772a1366c"
      }
    ],
    "programFingerprint": "874ae3751e0545f7c63bbc58890ba29e7620e3b081c9aca18e6bd4d7f177e50f",
    "requiredKinds": [
      "mentat.public-fec-tables.v1"
    ],
    "publicReaders": [
      "mentat.public-data.catalogue",
      "mentat.public-data.rows",
      "mentat.public-data.download",
      "mentat.public-data.provenance"
    ],
    "privateBoundaries": [
      "mentat.original.console",
      "mentat.original.console-root",
      "mentat.original.reports",
      "mentat.original.report-cache"
    ],
    "startupTimeoutMs": 300000
  }
});
module.exports=Object.freeze({APPLICATION_SPECS});
