export const MessageContainer = ({message, time, position}) => {
    return (
        <div className="chat__message">
            <p>{position ? 'Answer' : 'Question'}</p>
            <p>{message}</p>
            <p>{time}</p>
        </div>
    )
}