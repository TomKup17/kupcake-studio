# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Pevné revize a SHA-256 modelů, které aplikace stahuje. VYGENEROVÁNO nastroje/vytvor_manifest.py –
neupravovat ručně. Každý stažený soubor se proti tomuto seznamu ověří (stahovani.py)."""

# repo → {revize: commit, soubory: {jméno: (velikost v B, SHA-256)}}
HUGGINGFACE = {
    'Systran/faster-whisper-large-v3': {
        "revize": 'edaa852ec7e145841d8ffdb056a99866b5f0a478',
        "soubory": {
            'config.json': (2394, 'a9306624f5ec14270a014b647e5c316b6e03a662c369758d1b90697a7b0655b9'),
            'preprocessor_config.json': (340, '7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711'),
            'tokenizer.json': (2480617, '6d8cbd7cd0d8d5815e478dac67b85a26bbe77c1f5e0c6d76d1ce2abc0e5f21ca'),
            'vocabulary.json': (1068114, 'c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1'),
            'model.bin': (3087284237, '69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1'),
        },
    },
    'dropbox-dash/faster-whisper-large-v3-turbo': {
        "revize": '0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf',
        "soubory": {
            'config.json': (2263, 'b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e'),
            'preprocessor_config.json': (340, '7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711'),
            'tokenizer.json': (2710337, '297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd'),
            'vocabulary.json': (1068114, 'c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1'),
            'model.bin': (1617884929, 'e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da'),
        },
    },
    'Systran/faster-whisper-medium': {
        "revize": '08e178d48790749d25932bbc082711ddcfdfbc4f',
        "soubory": {
            'config.json': (2257, '3622a2ddc41ec0e0fd4e68c13c6830f03b90c38d89aaad184de02c8c642cf807'),
            'tokenizer.json': (2203239, 'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab'),
            'vocabulary.txt': (459861, '34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913'),
            'model.bin': (1527906378, '9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae'),
        },
    },
    'comodoro/wav2vec2-xls-r-300m-cs-250': {
        "revize": '73e2b9004f35d3ca79316a624e7edc3cdaa45d40',
        "soubory": {
            'config.json': (2061, '35d09d7133b26340c9e701e84aca947ed27a8256b9b2988dfcf18a5bdab3440f'),
            'vocab.json': (469, '1d646d6bdb317d6ab037994ad52eddefe51ddade07727fa41b5a05ad76e0ffd2'),
            'preprocessor_config.json': (262, '2c594304e9d9832162bedd5345051df29e8daf458a845cbed58c6ede23ceeae3'),
            'tokenizer_config.json': (300, 'b0626ad58b7eeb65a115845531226942bd0ce17a091f72674ec3062a2ecb074c'),
            'special_tokens_map.json': (309, 'fe9499f3f127cf340419ded12d4175b3a28a58c99c949bf3f8343a6f6b9fa872'),
            'added_tokens.json': (23, '462236017bb79296545ff6db99d980cd981258a0ec05dc225a6d1b1774df8aed'),
            'model.safetensors': (1261996032, '99376277738caade67bf57b7dfab362b3172323b4724c0db4c51a56254340099'),
        },
    },
    'comodoro/wav2vec2-xls-r-300m-sk-cv8': {
        "revize": 'caba6c9c8800778823ce75d96bed9ee2eb56ea3a',
        "soubory": {
            'config.json': (2067, 'fcbc6ec5f42c5f2687adf9b88b0cfeecb65a6c735842ca69105c68faa7a37892'),
            'vocab.json': (439, '682087b788a6f3db7219ebf90f02564fe156e977f48841907c46356d70f3a0fb'),
            'preprocessor_config.json': (256, 'ffc72f475cd79680d5d659fbaefc691cdbcee5c9703a15faf708a5e91452a8d8'),
            'tokenizer_config.json': (300, 'b0626ad58b7eeb65a115845531226942bd0ce17a091f72674ec3062a2ecb074c'),
            'special_tokens_map.json': (309, 'fe9499f3f127cf340419ded12d4175b3a28a58c99c949bf3f8343a6f6b9fa872'),
            'added_tokens.json': (23, '6738224214b5e9394fea55903f7f2483cd175609039df889a2ae97299e35b702'),
            'pytorch_model.bin': (1262124593, '721ace680bba9be71df42335fd08f2b631aa72bdd168b1804d9eb98fd9e25c90'),
        },
    },
    'facebook/wav2vec2-base-960h': {
        "revize": '22aad52d435eb6dbaf354bdad9b0da84ce7d6156',
        "soubory": {
            'config.json': (1596, 'd3ec255c063d9f95057b553b19c20135b259875834a4fe9deb218a6be25b4cf3'),
            'vocab.json': (291, '19727f8944fe6459fc3f240ae2c198395b740f6a029bd23e06656266b83bcf64'),
            'preprocessor_config.json': (159, 'b225d617c025463b9e157e06afea8b90dc7078fc70b013c533328423e0486b4a'),
            'tokenizer_config.json': (163, 'dc790594f5bc351a4311c6624f40acd95850d4aaf2a5cb3c656c9b610720b608'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'model.safetensors': (377607901, '8aa76ab2243c81747a1f832954586bc566090c83a0ac167df6f31f0fa917d74a'),
        },
    },
    'jonatasgrosman/wav2vec2-large-xlsr-53-german': {
        "revize": '4b8a02957378d0f2da2ef74091156b032c485a89',
        "soubory": {
            'config.json': (1782, '42175a918795a7343c58dbcad995603912a0d85c729cc4d7b8eb089a7a569183'),
            'vocab.json': (350, '31d0914432f4492a24ce83abfd767421844afe5cef20346a48c6c877dee28378'),
            'preprocessor_config.json': (262, 'ca5999a45e98bb76ea87a461ba28a23ad32a5bb9f733b8e0f6546ff38b6c612d'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'pytorch_model.bin': (1262089623, 'bff6d75ab89d8ca9cd103df9beb9c10f547501cf5a34aeabea1c8d736c1b81cb'),
        },
    },
    'jonatasgrosman/wav2vec2-large-xlsr-53-spanish': {
        "revize": '96d7e9b4e4a78af515a3c6d3cee7c0826045d276',
        "soubory": {
            'config.json': (1531, '39ffe954848d5161270eef4378a17a538bffeefc310482f409ec099f7fceaa5b'),
            'vocab.json': (380, '7aea8bcd8ba1c176f12cc96c1e8f45247548f4de3218106f7352e3d833cfafdc'),
            'preprocessor_config.json': (262, 'ca5999a45e98bb76ea87a461ba28a23ad32a5bb9f733b8e0f6546ff38b6c612d'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'pytorch_model.bin': (1262101911, '41c110e55d2eac8c79486ad87dbe8f9527ed034fe087a6adf03c891eeba914c1'),
        },
    },
    'jonatasgrosman/wav2vec2-large-xlsr-53-french': {
        "revize": '7c79e105a6525d38e1e69f640b974b4a679723cc',
        "soubory": {
            'config.json': (1531, 'ee87cfb5a4ad72d24b79eb26ab4b7c26ecc2adc1c0e0e6bc6c91e551d884ef43'),
            'vocab.json': (560, 'e83a3c849e480757fabd9fe927b870581e926407bcc7e1b6dcc8bda1e78a8d78'),
            'preprocessor_config.json': (262, 'ca5999a45e98bb76ea87a461ba28a23ad32a5bb9f733b8e0f6546ff38b6c612d'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'pytorch_model.bin': (1262175703, '2fc4760bab7bf7d0d6c06e9b7f829a27a3e66eefee3733f53c88dbedf6607f2e'),
        },
    },
    'jonatasgrosman/wav2vec2-large-xlsr-53-italian': {
        "revize": 'dab04a3e00d8326052f3fb22a6ff276b822f6131',
        "soubory": {
            'config.json': (1782, '7e69e919b00b2044006c69cea10a0b15d35d65b6acec9f7180afef2edc7df1fb'),
            'vocab.json': (410, 'deee9194b91e4e4f628ff37da6226a9c9cfe564810c917ae545920458723c58e'),
            'preprocessor_config.json': (262, 'ca5999a45e98bb76ea87a461ba28a23ad32a5bb9f733b8e0f6546ff38b6c612d'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'pytorch_model.bin': (1262114199, '14040a54d1e0caecd8b2271fdd2d96653be45702c7bc8765354140d864fb445a'),
        },
    },
    'jonatasgrosman/wav2vec2-large-xlsr-53-polish': {
        "revize": '6b1cea36bd8bc5f65ec8081667cd9c0207d51970',
        "soubory": {
            'config.json': (1782, '819dac7fa3ad7f4c11c15c2ede5f323effc5bcfaa311645a250392b65524c29c'),
            'vocab.json': (372, 'bf4603ae2fc39fa1e10a633b533c7535d7d6ffeb21181b6200c403264569cd0e'),
            'preprocessor_config.json': (262, 'ca5999a45e98bb76ea87a461ba28a23ad32a5bb9f733b8e0f6546ff38b6c612d'),
            'special_tokens_map.json': (85, 'bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675'),
            'pytorch_model.bin': (1262097815, '1bd2a29f3b6093cc7a0f9ad39d56b5b11ae00f588878035e117e379dd3c204a6'),
        },
    },
    'MahmoudAshraf/mms-300m-1130-forced-aligner': {
        "revize": '49402e9577b1158620820667c218cd494cc44486',
        "soubory": {
            'config.json': (2076, '2af7f73073d212b0ef91d3c73839355ca504c24a6b361c58a9e4e64210376ba9'),
            'vocab.json': (286, '6b6f1632d08b489faf2c954eb70e71f39d0861053feb9ae40da59cfa8d0ef5bb'),
            'preprocessor_config.json': (211, '6334d6e0c5f2084c9a99b85ddff243cbc79dbaa4aa790bcddf8c41c496fab6fb'),
            'tokenizer_config.json': (1047, 'e0fe11ce3a3231f3147b4539a93b30a9aefaca0c2717fbd35881695610417497'),
            'special_tokens_map.json': (74, '5e4d1f5e759d74cb1c2fe1d165cfc62b5237aa904de759380cd6f43042eec723'),
            'model.safetensors': (1261930388, '9aa5229a1af4d7714285cfa14bcaab6af2a39a9e810b475722b24975d5cb1dab'),
        },
    },
}

# Demucs htdemucs (oddělení hlasu) – oficiální úložiště Meta
DEMUCS = {'url': 'https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th', 'velikost': 84141911, 'sha256': '8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'}
