<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xsl:stylesheet [
	<!ENTITY nbsp "&#160;"> 
	<!ENTITY mdash "&#8212;"> 
]>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fo="http://www.w3.org/1999/XSL/Format" version="1.0">
	<xsl:include href="PopulateTemplate.xsl"/>
	<xsl:include href="AddHeader.xsl"/>
	<xsl:include href="CommonPathRef.xsl"/>
	<xsl:include href="AddOnTable.xsl"/>
	<xsl:include href="IRS1120HStyle.xsl"/>
	<xsl:output method="html" indent="yes"/>
	<xsl:strip-space elements="*"/>
	<xsl:param name="FormData" select="$RtnDoc/IRS1120H"/>
	<xsl:template match="/">
		<xsl:text disable-output-escaping="yes">&lt;!DOCTYPE html&gt;</xsl:text>
		<html>
			<head>
				<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
				<title>
					<xsl:call-template name="FormTitle">
						<xsl:with-param name="RootElement" select="local-name($FormData)"/>
					</xsl:call-template>
				</title>
				<!-- No Browser Caching   -->
				<meta http-equiv="Pragma" content="no-cache"/>
				<meta http-equiv="Cache-Control" content="no-cache"/>
				<meta http-equiv="Expires" content="0"/>
				<!-- No Proxy Caching -->
				<meta http-equiv="Cache-Control" content="private"/>
				<!-- Define Character Set -->
				<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1"/>
				<meta name="Description" content="IRS Form 1120-H"/>
				<!-- javascript include -->
				<script language="JavaScript" src="{$ScriptPath}/FormDisplay.js" type="text/javascript"/>
				<xsl:call-template name="InitJS"/>
				<style type="text/css">
					<xsl:if test="not($Print) or $Print=''">
						<xsl:call-template name="IRS1120HStyle"/>
						<xsl:call-template name="AddOnStyle"/>
					</xsl:if>
				</style>
				<xsl:call-template name="GlobalStylesForm"/>
			</head>
			<body class="styBodyClass" style="width:187mm;">
				<xsl:call-template name="DocumentHeader"/>
				<!-- BEGIN FORM HEADER -->
				<div class="styStdDiv">
					<div class="styFNBox" style="width:30mm;height:17mm;">
						Form <span class="styFormNumber" style="font-size:18pt;">1120-H</span><br />
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData"/>
						</xsl:call-template><br />
						<span class="styAgency">Department of the Treasury</span>
						<span class="styAgency">Internal Revenue Service</span>
					</div>
					<div class="styFTBox" style="width:124mm;height:17mm;padding-top:0.5mm;">
						<span class="styMainTitle">U.S. Income Tax Return <br /> for Homeowners Associations</span>
						<div class="styFST" style="padding-top:2mm;">
							Go to <span style="font-style:italic;">www.irs.gov/Form1120H</span> for instructions and the latest information.
						</div>
					</div>
					<div class="styTYBox" style="width:32mm;height:17mm;">
						<div class="styOMB" style="width:32mm;">OMB No. 1545-0123</div>
						<div class="styTaxYear" style="text-align:center;padding-top:1mm;">
							20<span class="styTYColor">24</span>
						</div>
					</div>
				</div>
				<div class="styStdDiv styLNDesc" style="width:187mm;border-top:1px solid black;padding:1px;">
					For calendar year 2024 or tax year beginning 
					<span style="width:50mm;text-align:center;">
						<xsl:call-template name="PopulateReturnHeaderTaxPeriodBeginDate"/>
					</span>
					and ending 
					<span style="width:50mm;text-align:center;">
						<xsl:call-template name="PopulateReturnHeaderTaxPeriodEndDate"/>
					</span>
				</div>
				<div class="styStdDiv">
					<div class="styGenericDiv" style="width:145mm;border:2px solid black;">
						<div class="styGenericDiv" style="width:13mm;height:20mm;font-weight:bold;font-size:8pt;padding-left:6px;padding-top:5mm;">
							TYPE OR PRINT
						</div>
						<div class="styGenericDiv" style="width:130mm;padding-left:3px;border-left:1px solid black;">
							Name <br />
							<xsl:call-template name="PopulateReturnHeaderFiler">
								<xsl:with-param name="TargetNode">BusinessNameLine1Txt</xsl:with-param>
							</xsl:call-template>
							<xsl:if test="$RtnHdrData/Filer//AddressLine2Txt">
								<br/>
								<xsl:call-template name="PopulateReturnHeaderFiler">
									<xsl:with-param name="TargetNode">BusinessNameLine2Txt</xsl:with-param>
								</xsl:call-template>
							</xsl:if>
						</div>
						<div class="styGenericDiv" style="width:130mm;padding-left:3px;border-left:1px solid black;border-top:1px solid black;">
							Number, street, and room or suite no. If a P.O. box, see instructions. <br />
							<xsl:call-template name="PopulateReturnHeaderFiler">
								<xsl:with-param name="TargetNode">AddressLine1Txt</xsl:with-param>
							</xsl:call-template>
							<xsl:if test="$RtnHdrData/Filer//AddressLine2Txt">
								<br />
								<xsl:call-template name="PopulateReturnHeaderFiler">
									<xsl:with-param name="TargetNode">AddressLine2Txt</xsl:with-param>
								</xsl:call-template>
							</xsl:if>
						</div>
						<div class="styGenericDiv" style="width:130mm;padding-left:3px;padding-bottom:2px;border-left:1px solid black;border-top:1px solid black;">
							City or town, state or province, country, and ZIP or foreign postal code <br />
							<xsl:call-template name="PopulateReturnHeaderFiler">
								<xsl:with-param name="TargetNode">CityStateInfo</xsl:with-param>
							</xsl:call-template>
							<xsl:if test="$RtnHdrData/Filer/ForeignAddress">
								<span style="width:7px;"/>
								<xsl:call-template name="PopulateReturnHeaderFiler">
									<xsl:with-param name="TargetNode">CountryCd</xsl:with-param>
									<xsl:with-param name="MainForm" select="true()"/>
								</xsl:call-template>
							</xsl:if>
						</div>
					</div>
					<div class="styGenericDiv" style="width:41.5mm;height:9mm;padding-left:3px;border-top:1px solid black;">
						<span style="font-weight:bold;font-size:6pt;">Employer identification number</span> <br />
						<xsl:call-template name="PopulateReturnHeaderFilerTIN">
							<xsl:with-param name="EINChanged" select="true()"/>
						</xsl:call-template>
					</div>
					<div class="styGenericDiv" style="width:41.5mm;height:9mm;padding-left:3px;border-top:1px solid black;">
						Date association formed <br />
						<xsl:call-template name="PopulateMonthDayYear">
							<xsl:with-param name="TargetNode" select="$FormData/AssociationFormedDt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Form body -->
				<div class="styStdDiv" style="border-top:1px solid black;">
					<div class="styLNDesc" style="height:auto;width:100%;">
						Check if: <span style="width:4mm;"/> (1) 
						<input type="checkbox" class="styCkboxNM" style="margin-left:2px;" aria-label="Final Return">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/FinalReturnInd"/>
								<xsl:with-param name="BackupName">F1120HFinalReturnInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Final return
						<span style="width:14mm;"/> (2) 
						<input type="checkbox" class="styCkboxNM" style="margin-left:2px;" aria-label="Name Change">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/NameChangeInd"/>
								<xsl:with-param name="BackupName">F1120HNameChangeInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Name Change
						<span style="width:14mm;"/> (3) 
						<input type="checkbox" class="styCkboxNM" style="margin-left:2px;" aria-label="Address Change">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/AddressChangeInd"/>
								<xsl:with-param name="BackupName">F1120HAddressChangeInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Address Change
						<span style="width:14mm;"/> (4) 
						<input type="checkbox" class="styCkboxNM" style="margin-left:2px;" aria-label="Amended Return">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/AmendedReturnInd"/>
								<xsl:with-param name="BackupName">F1120HAmendedReturnInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Amended return
					</div>
				</div>
				<!-- Line A -->
				<div class="styStdDiv" style="border-top:1px solid black;">
					<div class="styLNLeftNumBoxSD">A</div>
					<div class="styLNDesc" style="height:auto;width:175mm;font-family:Arial;">
						Check type of homeowners association: 
						<input type="checkbox" class="styCkboxNM" style="margin-left:8px;" aria-label="Condominium Management Association">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/CondominiumMgmtAssociationInd"/>
								<xsl:with-param name="BackupName">F1120HCondominiumMgmtAssociationInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Condominium management association
						<input type="checkbox" class="styCkboxNM" style="margin-left:8px;" aria-label="Residential Real Estate Association">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/ResidentialREAssociationInd"/>
								<xsl:with-param name="BackupName">F1120HResidentialREAssociationInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Residential real estate association
						<input type="checkbox" class="styCkboxNM" style="margin-left:8px;" aria-label="Timeshare Association Ind">
							<xsl:call-template name="PopulateCheckbox">
								<xsl:with-param name="TargetNode" select="$FormData/TimeshareAssociationInd"/>
								<xsl:with-param name="BackupName">F1120HTimeshareAssociationInd</xsl:with-param>
							</xsl:call-template>
						</input>
						Timeshare association
					</div>
				</div>
				<!-- Line B -->
				<div class="styStdDiv" style="border-top:1px solid black;">
					<div class="styLNLeftNumBoxSD">B</div>
					<div class="styLNDesc">
						Total exempt function income. Must meet 60% gross income test. See instructions
						<span class="sty1120HDotLn">........</span>
					</div>
					<div class="styLNRightNumBox">B</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalExemptFunctionIncomeAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line C -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">C</div>
					<div class="styLNDesc">
						Total expenditures made for purposes described in 90% expenditure test. See instructions
						<span class="sty1120HDotLn">.....</span>
					</div>
					<div class="styLNRightNumBox">C</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalExpendituresTestAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line D -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">D</div>
					<div class="styLNDesc">
						Association's total expenditures for the tax year. See instructions
						<span class="sty1120HDotLn">.............</span>
					</div>
					<div class="styLNRightNumBox">D</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalExpendituresAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line E -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">E</div>
					<div class="styLNDesc">
						Tax-exempt interest received or accrued during the tax year
						<span class="sty1120HDotLn">...............</span>
					</div>
					<div class="styLNRightNumBoxNBB">E</div>
					<div class="styLNAmountBoxNBB">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxExemptInterestAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<div class="styStdDiv" style="text-align:center;padding-top:1px;padding-bottom:1px;font-size:8pt;border-top:1px solid black;border-bottom:1px solid black;">
					<strong>Gross Income </strong> (excluding exempt function income)
				</div>
				<!-- Line 1 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">1</div>
					<div class="styLNDesc">
						Dividends
						<span class="sty1120HDotLn">..............................</span>
					</div>
					<div class="styLNRightNumBox">1</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/DividendsAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 2 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">2</div>
					<div class="styLNDesc">
						Taxable interest
						<span class="sty1120HDotLn">............................</span>
					</div>
					<div class="styLNRightNumBox">2</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxableInterestAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 3 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">3</div>
					<div class="styLNDesc">
						Gross rents
						<span class="sty1120HDotLn">..............................</span>
					</div>
					<div class="styLNRightNumBox">3</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/GrossRentsAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 4 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">4</div>
					<div class="styLNDesc">
						Gross royalties
						<span class="sty1120HDotLn">.............................</span>
					</div>
					<div class="styLNRightNumBox">4</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/GrossRoyaltiesAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 5 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">5</div>
					<div class="styLNDesc">
						Capital gain net income (attach Schedule D (Form 1120))
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/CapitalGainNetIncomeAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">...............</span>
					</div>
					<div class="styLNRightNumBox">5</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/CapitalGainNetIncomeAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 6 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">6</div>
					<div class="styLNDesc">
						Net gain or (loss) from Form 4797, Part II, line 17 (attach Form 4797)
						<xsl:call-template name="LinkToLeftoverDataTableInline">
							<xsl:with-param name="Desc">Line 6 - Form 4684 Code</xsl:with-param>
							<xsl:with-param name="TargetNode" select="$FormData/TotalOrdinaryGainLossAmt/@form4684Cd"/>
						</xsl:call-template>
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/TotalOrdinaryGainLossAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">..........</span>
					</div>
					<div class="styLNRightNumBox">6</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalOrdinaryGainLossAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 7 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">7</div>
					<div class="styLNDesc">
						Other income (excluding exempt function income) (attach statement)
						<xsl:call-template name="LinkToLeftoverDataTableInline">
							<xsl:with-param name="Desc">Line 7 - Other Income Description</xsl:with-param>
							<xsl:with-param name="TargetNode" select="$FormData/OtherIncomeAmt/@otherIncomeDesc"/>
						</xsl:call-template>
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/OtherIncomeAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">..........</span>
					</div>
					<div class="styLNRightNumBox">7</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/OtherIncomeAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 8 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">8</div>
					<div class="styLNDesc">
						<strong>Gross income </strong> (excluding exempt function income). Add lines 1 through 7
						<span class="sty1120HDotLn">..........</span>
					</div>
					<div class="styLNRightNumBoxNBB">8</div>
					<div class="styLNAmountBoxNBB">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalIncomeAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<div class="styStdDiv" style="text-align:center;padding-top:1px;padding-bottom:1px;font-size:8pt;border-top:1px solid black;border-bottom:1px solid black;">
					<strong>Deductions </strong> (directly connected to the production of gross income, excluding exempt function income)
				</div>
				<!-- Line 9 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBoxSD">9</div>
					<div class="styLNDesc">
						Salaries and wages
						<span class="sty1120HDotLn">............................</span>
					</div>
					<div class="styLNRightNumBox">9</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/SalariesAndWagesAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 10 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">10</div>
					<div class="styLNDesc">
						Repairs and maintenance
						<span class="sty1120HDotLn">..........................</span>
					</div>
					<div class="styLNRightNumBox">10</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/RepairsAndMaintenanceAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 11 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">11</div>
					<div class="styLNDesc">
						Rents
						<span class="sty1120HDotLn">...............................</span>
					</div>
					<div class="styLNRightNumBox">11</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/RentsPaidAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 12 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">12</div>
					<div class="styLNDesc">
						Taxes and licenses
						<span class="sty1120HDotLn">............................</span>
					</div>
					<div class="styLNRightNumBox">12</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxesAndLicensesAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 13 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">13</div>
					<div class="styLNDesc">
						Interest
						<span class="sty1120HDotLn">...............................</span>
					</div>
					<div class="styLNRightNumBox">13</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/InterestDeductionAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 14 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">14</div>
					<div class="styLNDesc">
						Depreciation (attach Form 4562)
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/DepreciationAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">......................</span>
					</div>
					<div class="styLNRightNumBox">14</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/DepreciationAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 15 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">15</div>
					<div class="styLNDesc">
						Other deductions (attach statement)
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/OtherDeductionsAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">.....................</span>
					</div>
					<div class="styLNRightNumBox">15</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/OtherDeductionsAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 16 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">16</div>
					<div class="styLNDesc">
						<strong>Total deductions. </strong> Add lines 9 through 15
						<span class="sty1120HDotLn">....................</span>
					</div>
					<div class="styLNRightNumBox">16</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalDeductionAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 17 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">17</div>
					<div class="styLNDesc">
						Taxable income before specific deduction of $100. Subtract line 16 from line 8
						<span class="sty1120HDotLn">.........</span>
					</div>
					<div class="styLNRightNumBox">17</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxableIncmBfrSpcfdDolDedAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 18 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">18</div>
					<div class="styLNDesc">
						Specific deduction of $100
						<span class="sty1120HDotLn">.........................</span>
					</div>
					<div class="styLNRightNumBoxNBB">18</div>
					<div class="styLNAmountBoxNBB">$100</div>
				</div>
				<div class="styStdDiv" style="text-align:center;padding-top:1px;padding-bottom:1px;font-size:8pt;border-top:1px solid black;border-bottom:1px solid black;">
					<strong>Tax and Payments</strong>
				</div>
				<!-- Line 19 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">19</div>
					<div class="styLNDesc">
						<strong>Taxable income. </strong> Subtract line 18 from line 17
						<span class="sty1120HDotLn">...................</span>
					</div>
					<div class="styLNRightNumBox">19</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxableIncomeAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 20 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">20</div>
					<div class="styLNDesc">
						Enter 30% (0.30) of line 19. (Timeshare associations, enter 32% (0.32) of line 19.)
						<span class="sty1120HDotLn">.......</span>
					</div>
					<div class="styLNRightNumBox">20</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxableIncomeApplcblPctAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 21 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">21</div>
					<div class="styLNDesc">
						Tax credits (see instructions)
						<span class="sty1120HDotLn">.........................</span>
					</div>
					<div class="styLNRightNumBox">21</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxCreditsAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 22 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">22</div>
					<div class="styLNDesc">
						<strong>Total tax. </strong> Subtract line 21 from line 20. See instructions for recapture of certain credits
						<xsl:call-template name="LinkToLeftoverDataTableInline">
							<xsl:with-param name="Desc">Line 22 - Recapture Tax Code</xsl:with-param>
							<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt/@recaptureTaxCd"/>
						</xsl:call-template>
						<xsl:call-template name="LinkToLeftoverDataTableInline">
							<xsl:with-param name="Desc">Line 22 - Recapture Tax Amount</xsl:with-param>
							<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt/@recaptureTaxAmt"/>
						</xsl:call-template>
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">...</span>
					</div>
					<div class="styLNRightNumBox">22</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 23a -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">23a</div>
					<div class="styLNDesc" style="width:98mm;">
						Preceding year's overpayment credited to the current year
						<span class="sty1120HDotLn">.....</span>
					</div>
					<div class="styLNRightNumBox">23a</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/PriorYearOverpaymentCreditAmt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23b -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">b</div>
					<div class="styLNDesc" style="width:98mm;">
						Current year's estimated tax payments
						<span class="sty1120HDotLn">...........</span>
					</div>
					<div class="styLNRightNumBox">23b</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/EstimatedTaxPaymentsAmt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23c -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">c</div>
					<div class="styLNDesc" style="width:98mm;">
						Tax deposited with Form 7004
						<span class="sty1120HDotLn">..............</span>
					</div>
					<div class="styLNRightNumBox">23c</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxPaidForm7004Amt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23d -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">d</div>
					<div class="styLNDesc" style="width:98mm;">
						Credit for tax paid on undistributed capital gains (attach Form 2439)
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/TaxPaidOnUndistrCapGainsAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">.</span>
					</div>
					<div class="styLNRightNumBox">23d</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TaxPaidOnUndistrCapGainsAmt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23e -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">e</div>
					<div class="styLNDesc" style="width:98mm;">
						Credit for federal tax paid on fuels (attach Form 4136)
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/FuelTaxCreditAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">......</span>
					</div>
					<div class="styLNRightNumBox">23e</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/FuelTaxCreditAmt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23f -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">f</div>
					<div class="styLNDesc" style="width:98mm;">
						Elective payment election amount from Form 3800
						<xsl:call-template name="SetFormLinkInline">
							<xsl:with-param name="TargetNode" select="$FormData/ElectivePaymentAmt"/>
						</xsl:call-template>
						<span class="sty1120HDotLn">.......</span>
					</div>
					<div class="styLNRightNumBox">23f</div>
					<div class="styLNAmountBox" style="padding-right:0.5mm;">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/ElectivePaymentAmt"/>
						</xsl:call-template>
					</div>
					<div class="styLNRightNumBoxNBB" style="background-color:lightgrey;">&nbsp;</div>
					<div class="styLNAmountBoxNBB" style="">&nbsp;</div>
				</div>
				<!-- Line 23g -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox" style="padding-left:4.2mm;">g</div>
					<div class="styLNDesc">
						<strong>Total payments and credits. </strong> Combine lines 23a through 23f
						<span class="sty1120HDotLn">..............</span>
					</div>
					<div class="styLNRightNumBox">23g</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/TotalPaymentsAndCreditsAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 24 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">24</div>
					<div class="styLNDesc">
						<strong>Amount Owed. </strong> Subtract line 23g from line 22. See instructions
						<span class="sty1120HDotLn">.............</span>
					</div>
					<div class="styLNRightNumBox">24</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/BalanceDueAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 25 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">25</div>
					<div class="styLNDesc">
						<strong>Overpayment. </strong> Subtract line 22 from line 23g
						<span class="sty1120HDotLn">...................</span>
					</div>
					<div class="styLNRightNumBox">25</div>
					<div class="styLNAmountBox">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/OverpaymentSection/OverpaymentAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- Line 26 -->
				<div class="styStdDiv">
					<div class="styLNLeftNumBox">26</div>
					<div class="styLNDesc">
						Enter amount of line 25 you want: <strong>Credited to 2025 estimated tax </strong>
						<span style="width:30mm;text-align:right;padding-right:1mm;">
							<xsl:call-template name="PopulateAmount">
								<xsl:with-param name="TargetNode" select="$FormData/OverpaymentSection/AppliedToEsTaxAmt"/>
							</xsl:call-template>
						</span>
						<span style="font-weight:bold;float:right;padding-right:1mm;">Refunded</span>
					</div>
					<div class="styLNRightNumBoxNBB">26</div>
					<div class="styLNAmountBoxNBB">
						<xsl:call-template name="PopulateAmount">
							<xsl:with-param name="TargetNode" select="$FormData/OverpaymentSection/RefundAmt"/>
						</xsl:call-template>
					</div>
				</div>
				<!-- BEGIN Signature Section -->
				<div class="styStdDiv" style="border-bottom:1px solid black;border-top:1px solid black;">
					<div class="styGenericDiv" style="width:13mm;height:17mm;font-size:12pt;font-weight:bold;padding-top:3mm;border-right:1px solid black;">
						Sign Here
					</div>
					<div class="styGenericDiv" style="width:174mm;font-size:6pt;padding:0.5mm;">
						Under penalties of perjury, I declare that I have examined this return, including accompanying schedules and statements, 
						and to the best of my knowledge and belief, it is true, correct, and complete. Declaration of preparer (other than taxpayer) 
						is based on all information of which preparer has any knowledge.<br />
					</div>
					<div class="styGenericDiv" style="width:174mm;">
						<div class="styGenericDiv" style="width:56mm;">
							<span style="width:100%;height:6mm;border-bottom:1px solid black;border-right:1px solid black;vertical-align:bottom;padding-left:0.5mm;padding-top:2mm;">
								<xsl:call-template name="PopulateReturnHeaderOfficer">
									<xsl:with-param name="TargetNode">PersonNm</xsl:with-param>
								</xsl:call-template>
							</span>
							<span style="padding-left:1mm;">Signature of officer</span>
						</div>
						<div class="styGenericDiv" style="width:16mm;">
							<span style="width:100%;height:6mm;border-bottom:1px solid black;padding-left:0.5mm;padding-top:2mm;">
								<xsl:call-template name="PopulateReturnHeaderOfficer">
									<xsl:with-param name="TargetNode">SignatureDt</xsl:with-param>
								</xsl:call-template>
							</span>
							<span>Date</span>
						</div>
						<div class="styGenericDiv" style="width:56mm;margin-left:2mm;">
							<span style="width:100%;height:6mm;border-bottom:1px solid black;padding-top:2mm;">
								<xsl:call-template name="PopulateReturnHeaderOfficer">
									<xsl:with-param name="TargetNode">PersonTitleTxt</xsl:with-param>
								</xsl:call-template>
							</span>
							<span>Title</span>
						</div>
						<div class="styGenericDiv" style="width:42mm;height:11mm;border:3px solid black;margin-left:3px;font-family:Arial;padding-left:1mm;">
							<xsl:call-template name="PopulateSpan">
								<xsl:with-param name="TargetNode" select="$RtnHdrData/BusinessOfficerGrp/DiscussWithPaidPreparerInd"/>
							</xsl:call-template>
							May the IRS discuss this return<br/>with the preparer shown below?<br/> See instructions.
							<input type="checkbox" class="styCkboxNM" style="margin-right:2px;" aria-label="Discuss with paid preparer Yes">
								<xsl:call-template name="PopulateReturnHeaderOfficer">
									<xsl:with-param name="TargetNode">AuthorizeThirdPartyYesCheckbox</xsl:with-param>
									<xsl:with-param name="BackupName">IRS1120HAuthorizeThirdPartyYesCheckbox</xsl:with-param>
								</xsl:call-template>
							</input>
							<span>Yes</span>
							<input type="checkbox" class="styCkboxNM" style="margin-left:6px;margin-right:2px;" aria-label="Discuss with paid preparer No">
								<xsl:call-template name="PopulateReturnHeaderOfficer">
									<xsl:with-param name="TargetNode">AuthorizeThirdPartyNoCheckbox</xsl:with-param>
									<xsl:with-param name="BackupName">IRS1120HAuthorizeThirdPartyNoCheckbox</xsl:with-param>
								</xsl:call-template>
							</input>
							<span>No</span>
						</div>
					</div>
				</div>
				<!-- paid preparer -->
				<div class="styStdDiv"  style="width:187mm;font-size:6pt;">
					<div class="styGenericDiv" style="width:23mm;height:auto;padding-top:4mm;">
						<span class="styMainTitle" style="font-size:11pt;">
							Paid
							Preparer
							Use Only
						</span>
					</div>
					<div class="styGenericDiv" style="width:164mm;">
						<div class="styGenericDiv" style="width:164mm;border-style:solid;border-color:black;border-width:0px 0px 1px 0px;">
							<div class="styLNDesc" style="height:8mm;width:46.5mm;padding-top:0mm;border-right:1px solid black;border-left:1px solid black;padding-left:1mm;">Print/Type preparer's name<br/>
								<xsl:call-template name="PopulateText">
									<xsl:with-param name="TargetNode" select="$RtnHdrData/PreparerPersonGrp/PreparerPersonNm"/>
								</xsl:call-template>
							</div>
						<div class="styLNDesc" style="height:8mm;width:46.5mm;padding-top:0mm;border-right:1px solid black;padding-left:1mm;">
							Preparer's signature
						</div>
							<div class="styLNDesc" 
							style="height:8mm;width:15mm;border-right:1px solid black;padding-top:0mm;padding-left:1mm;">Date <br/>
								<br/>
								<xsl:call-template name="PopulateReturnHeaderPreparer">
									<xsl:with-param name="TargetNode">DatePrepared</xsl:with-param>
								</xsl:call-template>
							</div>
							<div class="styLNDesc"
							 style="height:8mm;width:18mm;border-right:1px solid  black;padding-top:0mm;vertical-align:top;padding-bottom:0mm;padding-left:1mm;">
								<label>
									<xsl:call-template name="PopulateLabel">
										<xsl:with-param name="TargetNode" select="$RtnHdrData/PreparerPersonGrp/SelfEmployedInd"/>
										<xsl:with-param name="BackupName">$RtnHdrDataPreparerPersonGrpSelfEmployed</xsl:with-param>
									</xsl:call-template>
									Check 
									<input class="styCkbox" aria-label="Preparer Person Self Employed" type="checkbox" style="width:4mm;">
										<xsl:call-template name="PopulateCheckbox">
											<xsl:with-param name="TargetNode" select="$RtnHdrData/PreparerPersonGrp/SelfEmployedInd"/>
											<xsl:with-param name="BackupName">$RtnHdrDataPreparerPersonGrpSelfEmployed</xsl:with-param>
										</xsl:call-template>
									</input>
									<span style="width:4.5px;"/>if<br/>self-employed
								</label>
							</div>
							<div class="styLNDesc" style="height:6mm;width:26mm;padding-top:0mm;padding-left:1mm;">PTIN
							<br/>
								<br/>
								<span style="width:6mm;"/>
								<xsl:if test="$RtnHdrData/PreparerPersonGrp/SSN">
									<xsl:call-template name="PopulateReturnHeaderPreparer">
										<xsl:with-param name="TargetNode">SSN</xsl:with-param>
									</xsl:call-template>
								</xsl:if>
								<xsl:if test="$RtnHdrData/PreparerPersonGrp/PTIN">
									<xsl:call-template name="PopulateReturnHeaderPreparer">
										<xsl:with-param name="TargetNode">PTIN</xsl:with-param>
									</xsl:call-template>
								</xsl:if>
							</div>
						</div>
						<div style="width:164mm;float:left;clear:none;border-style:solid;border-color:black;border-width:0px 0px 1px 0px;">
						<div class="styLNDesc" style="height:6mm;width:126mm;border-right:1px solid black;border-left:1px solid black;padding-left:1mm;">
								<span class="styGenericDiv" style="">Firm's name 
								<span style="width:2.2mm;"/>
									<span style="width:4px;"/>
								</span>
								<div class="styGenericDiv" style="padding-right:.5mm;">
									<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
										<xsl:with-param name="TargetNode">BusinessNameLine1Txt</xsl:with-param>
									</xsl:call-template>
									<br/>
									<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
										<xsl:with-param name="TargetNode">BusinessNameLine2Txt</xsl:with-param>
									</xsl:call-template>
								</div>
							</div>
							<div class="styLNDesc" style="height:6mm;width:32mm;padding-left:1mm;">Firm's EIN
								<span style="width:4px;"/>
								<xsl:choose>
									<xsl:when test="$RtnHdrData/PreparerFirmGrp/PreparerFirmEIN">
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">EIN</xsl:with-param>
										</xsl:call-template>
									</xsl:when>
									<xsl:otherwise>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">MissingEINReason</xsl:with-param>
										</xsl:call-template>
									</xsl:otherwise>
								</xsl:choose>
							</div>
						</div>
						<div style="width:164mm;float:left;clear:none;">
							<div class="styLNDesc" style="width:126mm;border-right:1px solid black;border-left:1px solid black;padding-left:1mm;min-height:8mm;height:auto;">
								<div class="styGenericDiv" style="padding-right:.5mm;">Firm's address 
								</div>
								<div class="styGenericDiv" style="padding-right:.5mm;">
									<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
										<xsl:with-param name="TargetNode">AddressLine1Txt</xsl:with-param>
									</xsl:call-template>
									<br/>
									<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
										<xsl:with-param name="TargetNode">AddressLine2Txt</xsl:with-param>
									</xsl:call-template>
									<br/>
									<xsl:if test="$RtnHdrData/PreparerFirmGrp/PreparerUSAddress">
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">CityNm</xsl:with-param>
										</xsl:call-template>,
										<span style="width:2px;"/>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">StateAbbreviationCd</xsl:with-param>
										</xsl:call-template>,
										<span style="width:2px;"/>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">ZIPCd</xsl:with-param>
										</xsl:call-template>
									</xsl:if>
									<xsl:if test="$RtnHdrData/PreparerFirmGrp/PreparerForeignAddress">
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">CityNm</xsl:with-param>
										</xsl:call-template>,
										<span style="width:2px;"/>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">ProvinceOrStateNm</xsl:with-param>
										</xsl:call-template>,
										<span style="width:2px;"/>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">ForeignPostalCd</xsl:with-param>
										</xsl:call-template>,
										<span style="width:2px;"/>
										<xsl:call-template name="PopulateReturnHeaderPreparerFirm">
											<xsl:with-param name="TargetNode">CountryCd</xsl:with-param>
										</xsl:call-template>
									</xsl:if>
								</div>
							</div>
							<div class="styLNDesc" style="width:37mm;padding-left:1mm;height:auto;word-break:break-all;"> 
								Phone no. 
								<xsl:call-template name="PopulateReturnHeaderPreparer">
									<xsl:with-param name="TargetNode">Phone</xsl:with-param>
								</xsl:call-template>
								<xsl:call-template name="PopulateReturnHeaderPreparer">
									<xsl:with-param name="TargetNode">ForeignPhone</xsl:with-param>
								</xsl:call-template>
							</div>
						</div>
					</div>
				</div>
				<div class="pageEnd" style="width:187mm;border-top:1px solid black;">
					<strong>For Paperwork Reduction Act Notice, see separate instructions. </strong>
					<span style="margin-left:20mm;">
						Cat. No. 11477H
					</span>
					<span style="float:right;">
						Form <span class="styBoldText" style="font-size:8pt;">1120-H</span> (2024)
					</span>
				</div>
				<!--Begin ADDITIONAL DATA SECTION -->
				<div style="width:187mm;clear:both;">
					<div class="styLeftOverTitleLine" id="LeftoverData">
						<br/>
						<div class="styLeftOverTitle">
						Additional Data        
					</div>
						<div class="styLeftOverButtonContainer">
							<input class="styLeftoverTableBtn" TabIndex="1" type="button" value="Return to Form" onclick="javascript:returnToWriteInImage();"/>
						</div>
					</div>
				</div>
				<table class="styLeftOverTbl">
					<xsl:call-template name="PopulateCommonLeftover">
						<xsl:with-param name="TargetNode" select="$FormData"/>
						<xsl:with-param name="DescWidth" select="100"/>
					</xsl:call-template>
					<xsl:call-template name="PopulateLeftoverRow">
						<xsl:with-param name="Desc">Line 6 - Form 4684 Code</xsl:with-param>
						<xsl:with-param name="TargetNode" select="$FormData/TotalOrdinaryGainLossAmt/@form4684Cd"/>
					</xsl:call-template>
					<xsl:call-template name="PopulateLeftoverRow">
						<xsl:with-param name="Desc">Line 7 - Other Income Description</xsl:with-param>
						<xsl:with-param name="TargetNode" select="$FormData/OtherIncomeAmt/@otherIncomeDesc"/>
					</xsl:call-template>
					<xsl:call-template name="PopulateLeftoverRow">
						<xsl:with-param name="Desc">Line 22 - Recapture Tax Code</xsl:with-param>
						<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt/@recaptureTaxCd"/>
					</xsl:call-template>
					<xsl:call-template name="PopulateLeftoverRowAmount">
						<xsl:with-param name="Desc">Line 22 - Recapture Tax Amount</xsl:with-param>
						<xsl:with-param name="TargetNode" select="$FormData/TotalTaxAmt/@recaptureTaxAmt"/>
					</xsl:call-template>
				</table>
				<br/>
			</body>
		</html>
	</xsl:template>
</xsl:stylesheet>