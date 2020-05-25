# -*- coding: utf-8 -*-
#{'sf_id':'','name':'','type':'','mode':},

ELEMENTS_INFO= [
    {'sf_id':'a3Q3A0000008kk2','name':'T&M | Consulting Work','type':'service','mode':'tm'},
    {'sf_id':'a3Q0Y000000Lnma','name':'T&M | Project Advisors','type':'service','mode':'tm'},

    {'sf_id':'a3Q0Y000000LqGi','name':'Generic | Consulting Work Monthly Fees','type':'subscription','mode':'fixed_price'},
    {'sf_id':'a3Q3A0000008kjy','name':'Fixed Price | Consulting Work','type':'service','mode':'fixed_price'},

    {'sf_id':'a3Q0Y000000Lo9X','name':'Generic | Revenue Milestones','type':'milestone','mode':False},
    {'sf_id':'a3Q3A0000008kjt','name':'Generic | 3rd Party Invoices','type':'milestone','mode':False},
    {'sf_id':'a3Q3A0000008kju','name':'Generic | Percentage Revenues','type':'milestone','mode':False},

    {'sf_id':'a3Q3A0000008kjv','name':'Generic | Monthly Fees per Unit','type':'subscription','mode':False},
    {'sf_id':'a3Q3A0000008kjw','name':'Generic | Monthly Fees','type':'subscription','mode':False},
]

###############################
# QUERIES #	
###############################

SELECT_GET_INVOICED_AMOUNT = """
    SELECT SUM(KimbleOne__NetAmount__c)
        FROM KimbleOne__InvoiceLineItem__c
"""


SELECT_GET_TIME_ENTRIES = """
    SELECT 
        Id,
        Migration_Index__c,
        KimbleOne__Category1__c,
        KimbleOne__Category2__c,
        KimbleOne__Category3__c,
        KimbleOne__Category4__c,
        KimbleOne__DeliveryElement__c,
        KimbleOne__InvoiceItemStatus__c,
        KimbleOne__Notes__c,
        KimbleOne__TimePeriod__c,
        KimbleOne__Resource__c,
        KimbleOne__InvoicingCurrencyEntryRevenue__c,
        KimbleOne__EntryUnits__c,
        KimbleOne__ActivityAssignment__c,
        VCLS_Status__c

        FROM KimbleOne__TimeEntry__c
"""

SELECT_GET_ELEMENT_DATA = """
    SELECT
        Id,
        Name,
        KimbleOne__DeliveryGroup__c,
        KimbleOne__OriginatingProposal__c,
        KimbleOne__Reference__c,
        Activity__c,
        KimbleOne__Product__c,
        Contracted_Budget__c,
        KimbleOne__InvoicingCurrencyContractRevenue__c

        FROM KimbleOne__DeliveryElement__c

"""

SELECT_GET_PROJECT_DATA = """
    SELECT
        Id,
        Name,
        OwnerId,
        KimbleOne__Reference__c,
        KimbleOne__Account__c,
        KimbleOne__Proposal__c,
        
        KimbleOne__InvoicingCurrencyIsoCode__c,
        Scope_of_Work_Description__c,
        Activity__c,
        KimbleOne__ExpectedEndDate__c,
        KimbleOne__ForecastStatus__c,
        KimbleOne__DeliveryStage__c

        FROM KimbleOne__DeliveryGroup__c

"""

SELECT_GET_PROPOSAL_DATA = """
    SELECT 
        Id, 
        Name,
        KimbleOne__Opportunity__c, 
        KimbleOne__DeliveryStartDate__c, 
        KimbleOne__BusinessUnit__c 

        FROM KimbleOne__Proposal__c
"""

SELECT_GET_MILESTONE_DATA = """
    SELECT 
        Id,
        Name,
        KimbleOne__DeliveryElement__c,
        KimbleOne__InvoicingCurrencyMilestoneValue__c,
        KimbleOne__InvoiceItemStatus__c,
        KimbleOne__MilestoneDate__c,
        KimbleOne__MilestoneStatus__c,
        KimbleOne__MilestoneType__c
        
        FROM KimbleOne__Milestone__c
"""

SELECT_GET_ASSIGNMENT_DATA = """
    SELECT 
        Id,
        KimbleOne__DeliveryGroup__c,
        KimbleOne__ResourcedActivity__c,
        KimbleOne__Resource__c,
        KimbleOne__ActivityRole__c,
        KimbleOne__ForecastUsage__c,
        KimbleOne__InvoicingCurrencyForecastRevenueRate__c,
        KimbleOne__InvoicingCurrencyRevenueRate__c
        
        FROM KimbleOne__ActivityAssignment__c
        
"""

SELECT_GET_ACTIVITY_DATA = """
    SELECT 
        Id,
        Name,
        KimbleOne__ActivityStatus__c,
        KimbleOne__DeliveryGroup__c,
        KimbleOne__DeliveryElement__c
    
        FROM KimbleOne__ResourcedActivity__c
        
"""

SELECT_GET_ANNUITY_DATA = """
    SELECT 
        Id,
        Name,
        KimbleOne__StartDate__c,
        KimbleOne__EndDate__c,
        KimbleOne__DeliveryElement__c,
        KimbleOne__InvoicingCurrencyRevenueRate__c,
        KimbleOne__InitialNumberOfUnits__c

        FROM KimbleOne__Annuity__c
"""



STORE_TEMP = """
KimbleOne__PerformanceAnalysis__c.KimbleOne__ActualRevenue__c.CONVERT:SUM - KimbleOne__PerformanceAnalysis__c.KimbleOne__ActualWIPValue__c.CONVERT:SUM
"""