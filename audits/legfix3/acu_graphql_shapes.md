# ACU GraphQL request shapes — captured live 2026-07-25 by Claude (browser network intercept)

Endpoint: POST https://www.americascreditunions.org/graphql
Content-Type: application/json. Public (no auth cookie needed for these). Browser fired both
from /advocacy/letters-testimonies; live count = 533.

## Operation 1: "search" (paginated id listing + count)
Request body (verbatim; paginate with offset, page size = limit; browser used limit 12):

{"operationName":"search","variables":{"offset":0,"limit":12,"query":"","filters":[{"tag":"default","conditions":[{"field":"storage_type","values":["advocacy_communication"]},{"field":"document_type_machine_name","operator":"IN","values":["policy_letter","comment_letter","joint_letters","congressional_testimony"]}]}],"sort":{"field":"name","order":"ASC"},"facets":[{"field":"document_type","min_count":1},{"field":"recipient_agency_name","min_count":1}]},"query":"query search($offset: Int, $limit: Int, $query: String, $facets: [InputSolrFacet], $filters: [InputSolrConditionsGroup], $sort: InputSort) {\n  allResults: solrSearch(\n    index: \"searchstax_index\"\n    langcode: \"en\"\n    offset: $offset\n    limit: $limit\n    facets: $facets\n    query: $query\n    filters: $filters\n    sort: $sort\n  ) {\n    count\n    documents {\n      ... on SolrDocument {\n        id\n        __typename\n      }\n      __typename\n    }\n    facets {\n      field\n      values {\n        count\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"}

Response shape: {"data":{"allResults":{"count":533,"documents":[{"id":"4681",...}],"facets":[...]}}}

## Operation 2: "AdvocacyQuery" (detail fetch for a batch of ids)
Request body (verbatim; id = string array from operation 1):

{"operationName":"AdvocacyQuery","variables":{"id":["1616","4656"],"limit":12,"sort_field":"name","direction":"ASC"},"query":"query AdvocacyQuery($id: [String], $limit: Int!, $sort_field: String!, $direction: EntityQuerySortOrder) {\n  entityQuery(\n    entityType: STORAGE\n    filter: {conditions: [{field: \"id\", value: $id}]}\n    limit: $limit\n    sort: {direction: $direction, field: $sort_field}\n  ) {\n    items {\n      id\n      label\n      entityBundle\n      ... on StorageAdvocacyCommunication {\n        type: fieldDocumentType {\n          label\n          __typename\n        }\n        fieldAsset {\n          ... on MediaAcquiaDamPdfAsset {\n            acquiaDamAssetId {\n              versionId\n              __typename\n            }\n            name\n            __typename\n          }\n          ... on MediaAcquiaDamDocumentsAsset {\n            acquiaDamAssetId {\n              versionId\n              __typename\n            }\n            name\n            __typename\n          }\n          __typename\n        }\n        fieldPublishDate {\n          formatted(format: \"c\")\n          __typename\n        }\n        fieldRecipientAgency {\n          label\n          __typename\n        }\n        fieldBusinessArea {\n          label\n          __typename\n        }\n        fieldMemberOnlyContent\n        fieldAdvocacyIssueTypes {\n          label\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"}

Notes for the fetcher: no bill-number field exists in the payload — H.R.8398/H.R.8413 detection is
against the letter label (title) text. No tracker-position endpoint was captured (the bill tracker is a
different surface); tracker mode is OMITTED per the W1 contract. Letters carry MULTIPLE issue tags
(nine-layer counts summed to 642 over 533 letters on 07-24).