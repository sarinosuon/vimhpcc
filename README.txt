   object TheTypes {
      type InputOutputSpecType = (InputData, OutputData)

      case class Problem(message: String,
                         source: String,
                         caller: String,
                         comment: String,
                         inputOutput: InputOutputSpecType = (FormInputData(), RowsOutputData()))

      type CheckResultType = Either[Seq[Problem], Boolean]

      type ValidationType = (String, Int) => CheckResultType

      type ApplicableCheckType = (Int) => Boolean
      type CheckType = (String, Int) => CheckResultType

      type ActionResult = Either[Seq[Problem], OutputData]
      type ActionType = (InputData, Int) => ActionResult
      type InvokableActionData = () => ActionData

    }
    
      case class ActionData (
        name: String = "<noname>",
        deps: Seq[ActionData] = Seq(),
        isApplicable: ApplicableCheckType = (_) => true,
        inputOutput: InputOutputSpecType = (FormInputData(), RowsOutputData()),
        action: ActionType = (inputData, level) => Right(EmptyOutputData()),
        validations: Seq[ValidationType] = Seq(),
        postChecks: Seq[CheckType] = Seq(),
        follow: Seq[() => ActionData] = Seq()  // closures used, so that we don't produce infinite loop
    )
    
    
